import hashlib
import os
import re
import tarfile
import uuid
from io import BytesIO

from django.conf import settings
from django.core.cache import cache

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

# PDF compile cache settings (configurable via Django settings)
_COMPILE_CACHE_TTL = getattr(settings, "STYLE_CACHE_TTL_SECONDS", 3600)  # 1 hour
_COMPILE_CACHE_MAX_BYTES = getattr(settings, "STYLE_CACHE_MAX_BYTES", 10 * 1024 * 1024)  # 10 MB


TEMPLATE = r"""
% renderer-v2
\documentclass[10pt]{article}

\usepackage[T1]{fontenc}
\usepackage{graphicx}
\usepackage{enumitem}
\usepackage[a4paper,bottom=6.4mm,left=14.11mm,right=14.11mm,top=12mm]{geometry}
\usepackage{titlesec}
\usepackage{tabularx}
\usepackage{booktabs}
\usepackage[table, svgnames]{xcolor}
\usepackage{hyphenat}
\usepackage{romannum}
\usepackage{anyfontsize}
\usepackage[pdftex]{hyperref}
\usepackage{fontawesome}
\usepackage[misc]{ifsym}
\usepackage{array}
\usepackage{xcolor}
\usepackage{tfrupee}

\definecolor{myblue}{RGB}{75,65,200}

\setlength{\parindent}{0pt}
\hyphenpenalty 10000

%%%%%%% Command for Thick hline %%%%%%%%%%
\makeatletter
\newcommand{\thickhline}{%
    \noalign {\ifnum 0=`}\fi \hrule height 0.7pt
    \futurelet \reserved@a \@xhline
}
\newcolumntype{"}{@{\hskip\tabcolsep\vrule width 0.7pt\hskip\tabcolsep}}
\newcolumntype{L}[1]{>{\raggedright\arraybackslash}p{#1}}
\newcolumntype{C}[1]{>{\centering\arraybackslash}p{#1}}
\newcolumntype{R}[1]{>{\raggedleft\arraybackslash}p{#1}}
\makeatother
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%%%%%%% Command Section Headers %%%%%%%%%%
\newcommand{\xfill}[2][1ex]{
	\dimen0=#2\advance\dimen0 by #1
	\leaders\hrule height \dimen0 depth -#1\hfill
}
\newcommand\xfilll[2][1ex]{
    \dimen0=#2\advance\dimen0 by #1
    \leaders\hrule height \dimen0 depth -#1\hfill
}
\newenvironment{localsize}[1]{
    \begingroup
    \fontsize{#1}{\baselineskip}\selectfont
}{
    \endgroup
}
\newcommand{\textlarge}[1]{{\fontsize{11}{13.5}\selectfont #1}}
\renewcommand{\section}[1]{
	\vspace{5pt}
	{\color{Blue}{\Large\scshape\raggedright #1\xfill[0pt]{0.5pt}}}
}
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%%%%%%% Command Subsection Headers %%%%%%%
\renewcommand{\subsection}[4]{
	\def\temp{#3}
	\vspace{5pt}
	\parbox{\linewidth}{
		\large
		{\color{Black} \textbf{#1} 
		\ifx\temp\empty
		\else
			{\textbf{|} #3}
		\fi
		\textbf{|} \textit{#4}}
         \hfill{\fontsize{9}{11}\selectfont[#2]}
	}

}
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%%%%%%%%% Date Formatting %%%%%%%%%%%%%%%%
\newcommand{\filldate}[1]{\strut\hfill {\small \textit{(#1)}}}
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%%%%%%% Set itemize formatting %%%%%%%%%%%
\renewcommand\labelitemi{\small$\bullet$}
\setlist[itemize]{itemsep=-0.5mm, topsep=2pt, leftmargin=15pt, after=\vspace{1pt}}
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

%%%%% Edit if you want long header %%%%%%%
% Long Header
\newif\iflong
\longtrue
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

__SPACING_SETUP__\begin{document}
\parindent=0em

__CONTENT__

\end{document}
"""


_PLACEHOLDER_PATTERN = None
_PLACEHOLDER_KEYS: frozenset = frozenset()


def fill_placeholders(preamble: str, values: dict) -> str:
    """
    Replace ``__KEY__`` placeholders in *preamble* using a single-pass regex
    substitution. A one-pass approach prevents double-substitution: user text
    containing ``__X__`` inside a replacement value is never re-expanded.

    ``values`` keys must include the surrounding underscores (e.g. ``"__CONTENT__"``).
    """
    global _PLACEHOLDER_PATTERN, _PLACEHOLDER_KEYS

    current_keys = frozenset(values.keys())
    if _PLACEHOLDER_PATTERN is None or current_keys != _PLACEHOLDER_KEYS:
        pattern = "|".join(re.escape(k) for k in sorted(values.keys()))
        _PLACEHOLDER_PATTERN = re.compile(pattern)
        _PLACEHOLDER_KEYS = current_keys

    return _PLACEHOLDER_PATTERN.sub(lambda m: values[m.group(0)], preamble)


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
    from resume_renderer.services.styling import FONTS, build_spacing_setup, resolve_style

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

    # Resolve style (never crashes — falls back to defaults for old/invalid data)
    style = resolve_style(resume)
    font_setup = FONTS[style["font"]]
    accent_hex = style["accent"].lstrip("#").upper()  # 6 uppercase hex digits, no leading '#'
    spacing_setup = build_spacing_setup(style.get("line_spacing", "1.00"), style.get("word_spacing", "1.00"))

    preamble = resume.visual_theme.latex_preamble
    if preamble.count("__SPACING_SETUP__") != 1:
        raise RuntimeError(
            f"Preamble for theme '{resume.visual_theme.key}' must contain '__SPACING_SETUP__' exactly once, "
            f"found {preamble.count('__SPACING_SETUP__')}."
        )

    values = {
        "__CONTENT__": "\n".join(sections_latex),
        "__FONT_SETUP__": font_setup,
        "__ACCENT_HEX__": accent_hex,
        "__SPACING_SETUP__": spacing_setup,
    }
    full_latex = fill_placeholders(preamble, values)

    # Safety net: no unfilled __PLACEHOLDER__ must remain
    leftover = re.search(r"__[A-Z0-9_]+__", full_latex)
    if leftover:
        raise RuntimeError(
            f"Unfilled LaTeX placeholder '{leftover.group()}' remains in the final document. "
            "Ensure seed_templates has been run and IITB_PREAMBLE contains all required placeholders."
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
    """Compile LaTeX into PDF bytes using a persistent Dockerized TeX Live container.

    Results are cached by SHA-256 of the latex string to avoid redundant compiles
    when the same document is requested multiple times (e.g. rapid style toggling).
    Each compile job runs in an isolated per-job subdirectory inside the container
    so concurrent requests cannot interfere with each other.
    """
    if _get_docker_client() is None:
        raise RuntimeError(
            "Docker client is not available. Start Docker Desktop and try again."
        )

    # -- Cache lookup --------------------------------------------------------
    latex_hash = hashlib.sha256(latex.encode("utf-8")).hexdigest()
    cache_key = f"pdf_compile_{latex_hash}"
    cached_pdf = cache.get(cache_key)
    if cached_pdf is not None:
        return cached_pdf

    # -- Compile in Docker with per-job workdir isolation --------------------
    container = _get_latex_container()
    job_id = uuid.uuid4().hex
    workdir = f"/usr/src/tex/{job_id}"

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
        # Create isolated job directory and place files in it
        container.exec_run(cmd=f"mkdir -p {workdir}")
        container.put_archive(workdir, tar_buffer.read())

        exit_code, out = container.exec_run(
            cmd=(
                f"timeout 30 pdflatex -interaction=nonstopmode "
                f"-output-directory={workdir} {workdir}/main.tex"
            ),
            workdir=workdir,
        )
        if exit_code != 0:
            logs = out.decode("utf-8", errors="replace")
            if exit_code == 124:
                raise RuntimeError(
                    "LaTeX compilation timed out after 30 seconds. "
                    "The document may be too complex or contain an infinite loop."
                )
            raise RuntimeError(
                f"LaTeX compilation failed (exit code {exit_code}).\n"
                f"Log excerpt:\n{logs[-3000:]}"
            )

        bits, _ = container.get_archive(f"{workdir}/main.pdf")

        pdf_tar = BytesIO()
        for chunk in bits:
            pdf_tar.write(chunk)
        pdf_tar.seek(0)

        with tarfile.open(fileobj=pdf_tar, mode="r") as tar:
            pdf_file = tar.extractfile("main.pdf")
            if pdf_file is None:
                raise RuntimeError("PDF file not found in the container.")
            pdf_bytes = pdf_file.read()

        # Store in compile cache (skip if unusually large)
        if len(pdf_bytes) <= _COMPILE_CACHE_MAX_BYTES:
            cache.set(cache_key, pdf_bytes, _COMPILE_CACHE_TTL)

        return pdf_bytes

    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Unexpected docker error: {str(exc)}") from exc
    finally:
        # Always clean up the per-job workdir, even on failure
        try:
            container.exec_run(cmd=f"rm -rf {workdir}")
        except Exception:
            pass
