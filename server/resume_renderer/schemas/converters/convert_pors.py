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

    parts.append(
        r"""
%============================================================================
%   PoR SECTION
%----------------------------------------------------------------------------
\section*{\color{myblue}{\large POSITIONS OF RESPONSIBILITY}\xfilll[0pt]{0.5pt}}
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
\begin{{localsize}}{{11}}
\textbf{{{role}}} $\vert$ \it\small{{{organization}}} \hfill{{\it\small({duration})}}\vspace{{-7pt}}
\rule{{\linewidth}}{{0.4pt}}
\vspace{{-11pt}}
\end{{localsize}}
\\{{\it {summary}}}
\vspace{{-7pt}}
"""
            )

            parts.append(
                r"\begin{itemize}[label=\textcolor{myblue}{\textbullet}, itemsep = -1.2 mm, leftmargin=*]"
            )

            for bullet in bullets:
                parts.append(rf"\item {MARKDOWN_PARSER.parse(sanitize_text(bullet))}")

            parts.append(r"\end{itemize}")

        except KeyError as e:
            raise ValueError(f"Missing key in PoR data: {e}")
        except ValueError as e:
            raise ValueError(f"Invalid data in PoR: {e}")

    return "\n".join(parts)
