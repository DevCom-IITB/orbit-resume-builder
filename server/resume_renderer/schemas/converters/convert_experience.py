"""
Converts experience JSON data into LaTeX format for the resume.

example json:
[
    {
        "title": "Software Engineer Intern",
        "organization": "Google",
        "location": "Mountain View, CA",
        "timeline": "June 2023 - August 2023",
        "bullets": [
            "Developed a new feature for Google Search that improved user engagement by 10%",
            "Collaborated with a team of 5 engineers using Agile methodologies",
            "Implemented unit tests and integration tests to ensure code quality"
        ]
    },
    {
        "title": "Research Assistant",
        "organization": "Indian Institute of Technology, Bombay",
        "location": "Mumbai, India",
        "timeline": "January 2022 - May 2023",
        "bullets": [
            "Conducted research on machine learning algorithms for natural language processing",
            "Published a paper in the proceedings of the International Conference on Machine Learning (ICML)
        ]
    }
]
"""

from ...services.json_sanitizer import sanitize_text
from ...services.markdown_parser import MARKDOWN_PARSER


def convert_experience(experiences: list) -> str:
    """Convert experience JSON into LaTeX.

    Args:
        experiences: A list of dictionaries, each containing 'title', 'organization', 'location',
                        'timeline', and 'bullets'.

    Returns:
        A string containing the LaTeX code for the experience section of the resume.

    Raises:
        ValueError: If the input data is not in the expected format.
    """
    parts: list[str] = []

    if not isinstance(experiences, list):
        raise ValueError("Input must be a list of experiences.")

    if not experiences:
        return ""

    parts.append(
        r"""
%============================================================================
%   Experience SECTION
%----------------------------------------------------------------------------
\section*{\color{myblue}{\large PROFESSINAL EXPERIENCE}\xfilll[0pt]{0.5pt}}
"""
    )

    for exp in experiences:
        try:
            title = MARKDOWN_PARSER.parse(sanitize_text(exp["title"]))
            organization = MARKDOWN_PARSER.parse(sanitize_text(exp["organization"]))
            timeline = MARKDOWN_PARSER.parse(sanitize_text(exp["timeline"]))
            location = MARKDOWN_PARSER.parse(sanitize_text(exp["location"]))
            bullets = exp["bullets"]

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
\\{{\it {location}}}\\
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
            raise ValueError(f"Missing key in experience data: {e}")
        except ValueError as e:
            raise ValueError(f"Invalid data in experience: {e}")

    return "\n".join(parts)
