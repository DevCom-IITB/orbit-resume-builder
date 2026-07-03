import os
import tarfile
from io import BytesIO

try:
    import docker
except Exception:
    docker = None


client = None
if docker is not None:
    try:
        client = docker.from_env()
    except Exception:
        client = None


def _get_docker_client():
    """Return a live Docker client, reconnecting if the module was imported too early."""
    global client

    if client is not None:
        return client

    if docker is None:
        return None

    try:
        client = docker.from_env()
    except Exception:
        client = None

    return client

LATEX_IMAGE_NAME = os.getenv("LATEX_IMAGE_NAME", "resume-renderer:latest")
DOCKERFILE_PATH = os.path.join(os.path.dirname(__file__), "..", "Dockerfile")


def ensure_image_exists(force_rebuild=False):
    """Build the LaTeX image if it is not already available locally."""
    current_client = _get_docker_client()
    if current_client is None:
        raise RuntimeError(
            "Docker client is not available. Install docker SDK and ensure Docker daemon is running."
        )

    if force_rebuild:
        print("Force rebuilding the LaTeX image...")
        try:
            current_client.images.remove(LATEX_IMAGE_NAME, force=True)
        except Exception:
            pass  # Image doesn't exist, no need to remove
    try:
        current_client.images.get(LATEX_IMAGE_NAME)
    except Exception:
        if not os.path.exists(DOCKERFILE_PATH):
            raise RuntimeError(f"Dockerfile not found at {DOCKERFILE_PATH}")

        dockerfile_dir = os.path.dirname(DOCKERFILE_PATH)
        current_client.images.build(
            path=dockerfile_dir,
            tag=LATEX_IMAGE_NAME,
            dockerfile="Dockerfile",
            rm=True,
        )


LATEX_CACHE_VOLUME = "latex-cache"
cache_volume = None
_cache_client = _get_docker_client()
if _cache_client is not None:
    try:
        cache_volume = _cache_client.volumes.get(LATEX_CACHE_VOLUME)
    except Exception:
        try:
            cache_volume = _cache_client.volumes.create(LATEX_CACHE_VOLUME)
        except Exception:
            cache_volume = None


def assemble_resume_latex(resume) -> str:
    """
    Assembles the full LaTeX document for a Resume instance.
    Uses the resume's visual_theme for the preamble and converter set.
    Updates resume.cached_latex and resume.latex_cache_valid.
    """
    cache_marker = "% renderer-v2"
    if resume.latex_cache_valid and resume.cached_latex and cache_marker in resume.cached_latex:
        return resume.cached_latex

    from resume_renderer.schemas.converter_registry import get_converter

    converter_set_key = resume.visual_theme.converter_set_key
    config_override = resume.config_override or {}
    sections_latex = []

    for section in resume.sections.filter(is_visible=True).order_by("order").select_related("section_type"):
        stdef = section.section_type
        try:
            converter_fn = get_converter(converter_set_key, stdef.key)
        except KeyError:
            continue

        done_entries = section.entries.filter(generation_status="done").order_by("order")

        if stdef.allow_multiple_entries:
            # Each entry's content may be a single dict OR a list (LLM returns arrays).
            # Flatten so converters always receive a flat list of items.
            section_data = []
            for e in done_entries:
                if e.content is None:
                    continue
                if isinstance(e.content, list):
                    section_data.extend(e.content)
                else:
                    section_data.append(e.content)
        else:
            first = done_entries.first()
            section_data = first.content if first else None

        if not section_data:
            continue

        try:
            section_latex = converter_fn(section_data, config_override)
        except TypeError:
            section_latex = converter_fn(section_data)

        sections_latex.append(section_latex)

    #preamble = (resume.visual_theme.latex_preamble or "").strip() or TEMPLATE
    full_latex = resume.visual_theme.latex_preamble.replace(
    "__CONTENT__", "\n".join(sections_latex)
)

    resume.cached_latex = full_latex
    resume.latex_cache_valid = True
    resume.save(update_fields=["cached_latex", "latex_cache_valid"])
    return full_latex


LATEX_CONTAINER_NAME = os.getenv("LATEX_CONTAINER_NAME", "latex-renderer")


def _get_latex_container():
    """Find the named running LaTeX container. Raises clearly if it isn't up."""
    current_client = _get_docker_client()
    if current_client is None:
        raise RuntimeError(
            "Docker client is not available. Start Docker Desktop and try again."
        )

    try:
        container = current_client.containers.get(LATEX_CONTAINER_NAME)
        if container.status == "running":
            return container
        raise RuntimeError(
            f"Container '{LATEX_CONTAINER_NAME}' exists but is not running "
            f"(status: {container.status}). Start it with:\n"
            f"  docker start {LATEX_CONTAINER_NAME}"
        )
    except docker.errors.NotFound:
        raise RuntimeError(
            f"Container '{LATEX_CONTAINER_NAME}' not found. Start it with:\n"
            f"  docker run -d --name {LATEX_CONTAINER_NAME} "
            f"--memory=1.5g -v {LATEX_CACHE_VOLUME}:/root/.cache/texmf "
            f"{LATEX_IMAGE_NAME} sleep infinity"
        )


def compile_latex(latex: str) -> bytes:
    """Compile LaTeX into PDF bytes using a persistent Dockerized TeX Live container."""
    if _get_docker_client() is None:
        raise RuntimeError(
            "Docker client is not available. Start Docker Desktop and try again."
        )

    container = _get_latex_container()

    try:
        encoded = latex.encode("utf-8")

        tar_buffer = BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
            info = tarfile.TarInfo(name="main.tex")
            info.size = len(encoded)
            tar.addfile(tarinfo=info, fileobj=BytesIO(encoded))

            # Include logo files inside the container working directory if they exist
            base_dir = os.path.dirname(os.path.dirname(__file__))
            for filename in ["iitb-logo.png", "iitb-logo.jpeg"]:
                logo_path = os.path.join(base_dir, filename)
                if os.path.exists(logo_path):
                    with open(logo_path, "rb") as f:
                        logo_data = f.read()
                    logo_info = tarfile.TarInfo(name=filename)
                    logo_info.size = len(logo_data)
                    tar.addfile(tarinfo=logo_info, fileobj=BytesIO(logo_data))

        tar_buffer.seek(0)
        container.put_archive("/usr/src/tex", tar_buffer.read())

        exit_code, out = container.exec_run(
            cmd="pdflatex -interaction=nonstopmode -output-directory=/usr/src/tex main.tex",
            workdir="/usr/src/tex",
        )
        if exit_code != 0:
            logs = out.decode("utf-8", errors="replace")
            raise RuntimeError(f"Compilation failed with exit code {exit_code}: {logs}")

        bits, _ = container.get_archive("/usr/src/tex/main.pdf")

        pdf_tar = BytesIO()
        for chunk in bits:
            pdf_tar.write(chunk)
        pdf_tar.seek(0)

        with tarfile.open(fileobj=pdf_tar, mode="r") as tar:
            pdf_file = tar.extractfile("main.pdf")
            if pdf_file is None:
                raise RuntimeError("PDF file not found in the container.")
            return pdf_file.read()
    except RuntimeError:
        # If compilation failed, the container is still healthy — keep it.
        raise
    except Exception as e:
        # On unexpected errors, reset the global so the next call gets a fresh container.
        global _latex_container
        _latex_container = None
        raise RuntimeError(f"Unexpected docker error: {str(e)}")
