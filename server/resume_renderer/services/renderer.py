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

\begin{document}
\parindent=0em

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
        raise
    except Exception as e:
        raise RuntimeError(f"Unexpected docker error: {str(e)}")
    finally:
        if container is not None:
            container.remove(force=True)
