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

LATEX_IMAGE_NAME = os.getenv("LATEX_IMAGE_NAME", "resume-renderer:latest")
DOCKERFILE_PATH = os.path.join(os.path.dirname(__file__), "..", "Dockerfile")


def ensure_image_exists(force_rebuild=False):
    """Build the LaTeX image if it is not already available locally."""
    if client is None:
        raise RuntimeError(
            "Docker client is not available. Install docker SDK and ensure Docker daemon is running."
        )

    if force_rebuild:
        print("Force rebuilding the LaTeX image...")
        try:
            client.images.remove(LATEX_IMAGE_NAME, force=True)
        except Exception:
            pass  # Image doesn't exist, no need to remove
    try:
        client.images.get(LATEX_IMAGE_NAME)
    except Exception:
        if not os.path.exists(DOCKERFILE_PATH):
            raise RuntimeError(f"Dockerfile not found at {DOCKERFILE_PATH}")

        dockerfile_dir = os.path.dirname(DOCKERFILE_PATH)
        client.images.build(
            path=dockerfile_dir,
            tag=LATEX_IMAGE_NAME,
            dockerfile="Dockerfile",
            rm=True,
        )


LATEX_CACHE_VOLUME = "latex-cache"
cache_volume = None
if client is not None:
    try:
        cache_volume = client.volumes.get(LATEX_CACHE_VOLUME)
    except Exception:
        try:
            cache_volume = client.volumes.create(LATEX_CACHE_VOLUME)
        except Exception:
            cache_volume = None


TEMPLATE = r"""
%============================================================================
\documentclass[a4paper,10.9pt]{article}
\usepackage[a4paper, bottom = 0.4mm, left = 14.11mm, right = 14.11mm, top = 0.6in]{geometry}
\usepackage{lmodern}
\usepackage{graphicx}
\usepackage{amsmath}
\usepackage{array}
\usepackage{enumitem}
%\usepackage{enumitem,xcolor}
\usepackage{microtype}
\usepackage{tabularx}
\usepackage{wrapfig}
\usepackage{titlesec}
\usepackage{comment}
\usepackage{verbatim}
\usepackage[dvipsnames]{xcolor}
\usepackage{hyperref}
\usepackage{colortbl}
\definecolor{myblue}{RGB}{75,65,200}
\newcommand{\xfilll}[2][1ex]{
\dimen0=#2\advance\dimen0 by #1
\leaders\hrule height \dimen0 depth -#1\hfill}
\titleformat{\section}{\Large\bfseries\color{myblue}\raggedright}{}{0em}{}
\titlespacing*{\section}{0pt}{2pt}{1pt}
\renewcommand\labelitemi{\raisebox{0.4ex}{\tiny$\bullet$}}
\renewcommand{\labelitemii}{$\cdot$}
\pagenumbering{gobble}

\newenvironment{localsize}[1]
{\fontsize{#1}{#1}\selectfont}
{}

% ---------- colours ----------
\definecolor{iitbblue}{RGB}{0, 51, 102}

% ---------- hyperlinks ----------
\hypersetup{
  colorlinks=true,
  urlcolor=iitbblue,
  linkcolor=iitbblue
}

% ---------- no page number ----------
\pagestyle{empty}

% ---------- helper: project / experience entry ----------
% Usage: \entry{Title | Role}{Organisation}{Location}{Date}
\newcommand{\entry}[4]{%
  \noindent
  \begin{tabularx}{\linewidth}{@{}X r@{}}
    \textbf{#1}  & \textit{#4} \\[-2pt]
    \textit{#2}  & \textit{#3} \\
  \end{tabularx}%
  \vspace{2pt}%
}

% ============================================================
\begin{document}

__CONTENT__

\end{document}
"""


def compile_latex(latex: str) -> bytes:
    """Compile LaTeX into PDF bytes using a Dockerized TeX Live image."""
    if client is None:
        raise RuntimeError(
            "Docker client is not available. Skipping LaTeX compilation."
        )

    ensure_image_exists(force_rebuild=False)
    container = None

    try:
        container = client.containers.run(
            image=LATEX_IMAGE_NAME,
            command="sleep infinity",
            working_dir="/usr/src/tex",
            detach=True,
            mem_limit="1.5g",
            nano_cpus=2_000_000_000,
            security_opt=["no-new-privileges"],
            volumes={LATEX_CACHE_VOLUME: {"bind": "/root/.cache/texmf", "mode": "rw"}},
        )

        full_document = TEMPLATE.replace("__CONTENT__", latex)
        # print(full_document) # Debug
        # return
        encoded = full_document.encode("utf-8")

        tar_buffer = BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
            info = tarfile.TarInfo(name="main.tex")
            info.size = len(encoded)
            tar.addfile(tarinfo=info, fileobj=BytesIO(encoded))

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
        raise
    except Exception as e:
        raise RuntimeError(f"Unexpected docker error: {str(e)}")
    finally:
        if container is not None:
            container.remove(force=True)
