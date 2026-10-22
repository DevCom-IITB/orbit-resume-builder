"""
Converts positions of responsibility JSON into IITB-format LaTeX.

Schema: role, organization, duration, summary, bullets
"""

from ...services.json_sanitizer import sanitize_text
from ...services.markdown_parser import MARKDOWN_PARSER


def convert_pors(positions: list) -> str:
    if not isinstance(positions, list):
        raise ValueError("Input must be a list of position entries.")
    if not positions:
        return ""

    parts = [
        r"""\section*{\color{myblue}{\large POSITIONS OF RESPONSIBILITY}\xfilll[0pt]{0.5pt}}
\vspace{-8pt}"""
    ]

    for pos in positions:
        try:
            role = MARKDOWN_PARSER.parse(sanitize_text(pos["role"]))
            organization = MARKDOWN_PARSER.parse(sanitize_text(pos["organization"]))
            duration = MARKDOWN_PARSER.parse(sanitize_text(pos.get("duration", "")))
            summary = MARKDOWN_PARSER.parse(sanitize_text(pos.get("summary", "")))
            bullets = pos.get("bullets", [])
            if not isinstance(bullets, list):
                raise ValueError("'bullets' must be a list.")

            org_part = rf" $\vert$\ \it\small{{{organization}}}" if organization else ""
            dur_part = rf"\hfill{{\small\it({duration})}}" if duration else ""

            entry = rf"""
\begin{{localsize}}{{11}}
{{\bf \noindent {role}}}{org_part} \vspace{{-7pt}}
{dur_part}
\rule{{\linewidth}}{{0.4pt}}
\end{{localsize}}
\vspace{{-11pt}}"""

            if summary:
                entry += rf"""
\\{{\it {summary}}}\\
\vspace{{-18pt}}"""

            entry += "\n" + r"\begin{itemize}[label=\textcolor{myblue}{\textbullet}, itemsep = -0.80 mm, leftmargin=*]"
            for bullet in bullets:
                b = MARKDOWN_PARSER.parse(sanitize_text(bullet))
                entry += f"\n    \\item {b}"
            entry += "\n" + r"\end{itemize}"
            parts.append(entry)
        except KeyError as e:
            raise ValueError(f"Missing key in position data: {e}")

    return "\n".join(parts)
