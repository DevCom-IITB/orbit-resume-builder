"""
To convert the positions of responsibility json data into latex

example input:
[
  {
    "role": "Developer",
    "organization": "Developer's Community, IIT Bombay",
    "duration": "Mar '25 - Present",
    "summary": "Part of DevCom, a 40+ member team responsible for building & managing crucial digital infrastructure for IIT Bombay",
    "bullets": [
      "Currently developing the Career and Research Portal, a centralized hub to connect 10,000+ students with 300+ professors, streamlining research project collaboration and fostering academic innovation across various disciplines",
      "Developing an AI Resume Builder, streamlining resume prep for internships, placements, & research roles"
    ]
  },
  {
    "role": "Core Member",
    "organization": "Aerospace Club",
    "duration": "Aug '24 - Present",
    "summary": "Working on aerospace research and technical projects",
    "bullets": [
      "Led technical workshops",
      "Collaborated on flight systems projects"
    ]
  }
]
"""

from ...services.json_sanitizer import sanitize_text
from ...services.markdown_parser import MARKDOWN_PARSER


def convert_pors(pors: list) -> str:
    """Convert positions of responsibility JSON into LaTeX.

    Args:
        pors: A list of dictionaries, each containing
              'role', 'organization', 'duration',
              'summary', and 'bullets'.

    Returns:
        A string containing the LaTeX code for the PoR section.

    Raises:
        ValueError: If the input data is not in the expected format.
    """
    parts: list[str] = []

    if not isinstance(pors, list):
        raise ValueError("Input must be a list of PoRs.")

    if not pors:
        return ""

    import re
    def format_year_hfill(text: str) -> str:
        return re.sub(r"\s+\[([^\]]+)\]\s*$", r" \\hfill[\1]", text)

    parts.append(
        r"""
%============================================================================
%   PoR SECTION
%----------------------------------------------------------------------------
\section{\textbf{Positions of Responsibility}}
"""
    )

    for por in pors:
        try:
            role = MARKDOWN_PARSER.parse(sanitize_text(por["role"]))
            organization = MARKDOWN_PARSER.parse(sanitize_text(por["organization"]))
            duration = MARKDOWN_PARSER.parse(sanitize_text(por["duration"]))
            summary = MARKDOWN_PARSER.parse(sanitize_text(por["summary"]))
            bullets = por["bullets"]

            if not isinstance(bullets, list):
                raise ValueError("'bullets' must be a list.")

            parts.append(
                rf"""
%----------------------------------------------------------------------------
\subsection{{{role}}}{{{duration}}}{{}}{{{organization}}}\vspace{{-5pt}}
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
            raise ValueError(f"Missing key in PoR data: {e}")
        except ValueError as e:
            raise ValueError(f"Invalid data in PoR: {e}")

    return "\n".join(parts)
