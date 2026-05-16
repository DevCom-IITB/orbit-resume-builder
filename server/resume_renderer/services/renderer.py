import os
import tarfile
from io import BytesIO

import docker


client = docker.from_env()

LATEX_IMAGE_NAME = os.getenv("LATEX_IMAGE_NAME", "resume-renderer:latest")
DOCKERFILE_PATH = os.path.join(os.path.dirname(__file__), "..", "Dockerfile")


def ensure_image_exists():
    """Build the LaTeX image if it is not already available locally."""
    try:
        client.images.get(LATEX_IMAGE_NAME)
    except docker.errors.ImageNotFound:
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
try:
    cache_volume = client.volumes.get(LATEX_CACHE_VOLUME)
except docker.errors.NotFound:
    cache_volume = client.volumes.create(LATEX_CACHE_VOLUME)


TEMPLATE = r"""
\documentclass[10pt, a4paper]{article}

% ---------- packages ----------
\usepackage[
  top=0.5in, bottom=0.5in,
  left=0.6in, right=0.6in
]{geometry}
\usepackage{array}
\usepackage{tabularx}
\usepackage{hyperref}
\usepackage{xcolor}

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

    ensure_image_exists()
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
