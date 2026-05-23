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

    parts.append(
        r"""
%============================================================================
%   Key Projects SECTION
%----------------------------------------------------------------------------
\section*{\color{myblue}{\large KEY PROJECTS}\xfilll[0pt]{0.5pt}}
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
\begin{{localsize}}{{11}}
{{\bf \noindent {title}}} $\vert$\ \it\small{{{organization}}}\vspace{{-7pt}}
\hfill{{\small\it({timeline})}}
\rule{{\linewidth}}{{0.4pt}}
\end{{localsize}}
\vspace{{-11pt}}
\\{{\it {summary}}}\\
\vspace{{-18pt}}
"""
            )

            parts.append(
                r"\begin{itemize}[label=\textcolor{myblue}{\textbullet}, itemsep = -0.75 mm, leftmargin=*]"
            )

            for bullet in bullets:
                bullet_text = MARKDOWN_PARSER.parse(sanitize_text(bullet))
                parts.append(rf"\item {bullet_text}")

            parts.append(r"\end{itemize}")

        except KeyError as e:
            raise ValueError(f"Missing key in project data: {e}")
        except ValueError as e:
            raise ValueError(f"Invalid data in project: {e}")

    return "\n".join(parts)
