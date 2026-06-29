"""
Converts professional experience JSON into IITB-format LaTeX.

Schema: title, organization, location, timeline, summary, bullets
"""

from ...services.json_sanitizer import sanitize_text
from ...services.markdown_parser import MARKDOWN_PARSER


def convert_experience(experiences: list) -> str:
    if not isinstance(experiences, list):
        raise ValueError("Input must be a list of experiences.")
    if not experiences:
        return ""

    parts = [
        r"""\section*{\color{myblue}{\large PROFESSIONAL EXPERIENCE}\xfilll[0pt]{0.5pt}}
\vspace{-8pt}"""
    ]

    for exp in experiences:
        try:
            title = MARKDOWN_PARSER.parse(sanitize_text(exp["title"]))
            organization = MARKDOWN_PARSER.parse(sanitize_text(exp["organization"]))
            location = MARKDOWN_PARSER.parse(sanitize_text(exp.get("location", "")))
            timeline = MARKDOWN_PARSER.parse(sanitize_text(exp["timeline"]))
            summary = MARKDOWN_PARSER.parse(sanitize_text(exp.get("summary", "")))
            bullets = exp.get("bullets", [])
            if not isinstance(bullets, list):
                raise ValueError("'bullets' must be a list.")

            loc_part = rf" $\vert$\ \it\small{{{location}}}" if location else ""

            entry = rf"""
\begin{{localsize}}{{11}}
{{\bf \noindent {title}}} $\vert$\ \it\small{{{organization}}}{loc_part} \vspace{{-7pt}}
\hfill{{\small\it({timeline})}}
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
            raise ValueError(f"Missing key in experience data: {e}")

    return "\n".join(parts)
