"""
Converts key project JSON into IITB-format LaTeX.

Schema: title, organization, summary, timeline, bullets
"""

from ...services.json_sanitizer import sanitize_text
from ...services.markdown_parser import MARKDOWN_PARSER


def convert_key_project(projects: list) -> str:
    if not isinstance(projects, list):
        raise ValueError("Input must be a list of project entries.")
    if not projects:
        return ""

    parts = [
        r"""\section*{\color{myblue}{\large KEY PROJECTS}\xfilll[0pt]{0.5pt}}
\vspace{-8pt}"""
    ]

    for proj in projects:
        try:
            title = MARKDOWN_PARSER.parse(sanitize_text(proj["title"]))
            organization = MARKDOWN_PARSER.parse(sanitize_text(proj.get("organization", "")))
            timeline = MARKDOWN_PARSER.parse(sanitize_text(proj.get("timeline", "")))
            summary = MARKDOWN_PARSER.parse(sanitize_text(proj.get("summary", "")))
            bullets = proj.get("bullets", [])
            if not isinstance(bullets, list):
                raise ValueError("'bullets' must be a list.")

            org_part = rf" $\vert$\ \it\small{{{organization}}}" if organization else ""
            time_part = rf"\hfill{{\small\it({timeline})}}" if timeline else ""

            entry = rf"""
\begin{{localsize}}{{11}}
{{\bf \noindent {title}}}{org_part} \vspace{{-7pt}}
{time_part}
\rule{{\linewidth}}{{0.4pt}}
\end{{localsize}}
\vspace{{-11pt}}"""

            if summary:
                entry += rf"""
\\{{\it {summary}}}\\
\vspace{{-18pt}}"""

            entry += "\n" + r"\begin{itemize}[label=\textcolor{myblue}{\textbullet}, itemsep = -0.75 mm, leftmargin=*]"
            for bullet in bullets:
                b = MARKDOWN_PARSER.parse(sanitize_text(bullet))
                entry += f"\n    \\item {b}"
            entry += "\n" + r"\end{itemize}"
            parts.append(entry)
        except KeyError as e:
            raise ValueError(f"Missing key in project data: {e}")

    return "\n".join(parts)
