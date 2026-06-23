"""
Converts key project JSON data into LaTeX format for the resume.

example json:
[
    {
        "title": "Machine Learning Research on Natural Language Processing",
        "organization": "Dr. John Doe",
        "summary": "Conducted research on machine learning algorithms for natural language processing, resulting in a publication in the proceedings of the International Conference on Machine Learning (ICML).",
        "timeline": "January 2022 - May 2023",
        "bullets": [
            "Conducted research on machine learning algorithms for natural language processing",
            "Published a paper in the proceedings of the International Conference on Machine Learning (ICML)"
        ]
    },
    {
        "title": "Web Development Project",
        "organization": "DevCom (IIT Bombay)",
        "summary": "Developed a full-stack web application using React and Node.js, implementing user authentication and real-time data updates.",
        "timeline": "June 2021 - December 2021",
        "bullets": [
            "Developed a full-stack web application using React and Node.js",
            "Implemented user authentication and real-time data updates"
        ]
    }
]
"""

from ...services.json_sanitizer import sanitize_text
from ...services.markdown_parser import MARKDOWN_PARSER


def convert_key_project(projects: list) -> str:
    """Convert key project JSON into LaTeX.

    Args:
        projects: A list of dictionaries, each containing
                  'title', 'organization', 'timeline',
                  'summary', and 'bullets'.

    Returns:
        A string containing the LaTeX code for the key projects section.

    Raises:
        ValueError: If the input data is not in the expected format.
    """
    parts: list[str] = []

    if not isinstance(projects, list):
        raise ValueError("Input must be a list of projects.")

    if not projects:
        return ""

    import re
    def format_year_hfill(text: str) -> str:
        return re.sub(r"\s+\[([^\]]+)\]\s*$", r" \\hfill[\1]", text)

    parts.append(
        r"""
%============================================================================
%   Key Projects SECTION
%----------------------------------------------------------------------------
\section{\textbf{Key Projects}}
"""
    )

    for proj in projects:
        try:
            title = MARKDOWN_PARSER.parse(sanitize_text(proj["title"]))
            organization = MARKDOWN_PARSER.parse(sanitize_text(proj["organization"]))
            timeline = MARKDOWN_PARSER.parse(sanitize_text(proj["timeline"]))
            summary = MARKDOWN_PARSER.parse(sanitize_text(proj["summary"]))
            bullets = proj["bullets"]

            if not isinstance(bullets, list):
                raise ValueError("'bullets' must be a list.")
            
            parts.append(
                rf"""
%----------------------------------------------------------------------------
\subsection{{{title}}}{{{timeline}}}{{}}{{{organization}}}\vspace{{-5pt}}
\rule{{\linewidth}}{{0.4pt}}
"""
            )

            if summary and summary.strip() != "":
                parts.append(rf"\textit{{{summary}}}\vspace{{2pt}}")

            parts.append(r"\begin{itemize}")

            for bullet in bullets:
                bullet_text = MARKDOWN_PARSER.parse(sanitize_text(bullet))
                bullet_text = format_year_hfill(bullet_text)
                parts.append(rf"    \item {bullet_text}")

            parts.append(r"\end{itemize}")

        except KeyError as e:
            raise ValueError(f"Missing key in project data: {e}")
        except ValueError as e:
            raise ValueError(f"Invalid data in project: {e}")

    return "\n".join(parts)
