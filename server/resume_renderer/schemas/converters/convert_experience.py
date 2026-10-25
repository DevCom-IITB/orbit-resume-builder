"""
Converts professional experience JSON into IITB-format LaTeX.

Schema: title, organization, location, timeline, summary, bullets
"""

from ...services.json_sanitizer import sanitize_text
from ...services.markdown_parser import MARKDOWN_PARSER
from .iitb_layout import ENTRY_GAP_PT, LIST_SECTION_END_GAP_PT, compute_gap


def convert_experience(experiences: list, config_override: dict = None) -> str:
    if not isinstance(experiences, list):
        raise ValueError("Input must be a list of experiences.")
    if not experiences:
        return ""

    parts = [
        r"""\section*{\color{myblue}{\large PROFESSIONAL EXPERIENCE}\xfilll[0pt]{0.5pt}}
\vspace{-8pt}"""
    ]

    total = len(experiences)
    for idx, exp in enumerate(experiences):
        try:
            title = MARKDOWN_PARSER.parse(sanitize_text(exp["title"]))
            organization = MARKDOWN_PARSER.parse(sanitize_text(exp["organization"]))
            location = MARKDOWN_PARSER.parse(sanitize_text(exp.get("location", "")))
            timeline = MARKDOWN_PARSER.parse(sanitize_text(exp["timeline"]))
            summary = MARKDOWN_PARSER.parse(sanitize_text(exp.get("summary", "")))
            raw_bullets = exp.get("bullets", [])
            if not isinstance(raw_bullets, list):
                raise ValueError("'bullets' must be a list.")
            bullets = [b for b in raw_bullets if isinstance(b, str) and b.strip()]

            loc_part = rf" $\vert$\ \it\small{{{location}}}" if location else ""

            entry = rf"""
\begin{{localsize}}{{11}}
{{\bf \noindent {title}}} $\vert$\ \it\small{{{organization}}}{loc_part} \vspace{{-7pt}}
\hfill{{\small\it({timeline})}}
\rule{{\linewidth}}{{0.4pt}}
\end{{localsize}}
\vspace{{-11pt}}"""

            if summary:
                if bullets:
                    entry += rf"""
\\{{\it {summary}}}\\
\vspace{{-18pt}}"""
                else:
                    entry += rf"""
\\{{\it {summary}}}"""

            if bullets:
                entry += "\n" + r"\begin{itemize}[label=\textcolor{myblue}{\textbullet}, itemsep = -0.75 mm, leftmargin=*]"
                for bullet in bullets:
                    b = MARKDOWN_PARSER.parse(sanitize_text(bullet))
                    entry += f"\n    \\item {b}"
                entry += "\n" + r"\end{itemize}"

            is_last = (idx == total - 1)
            base_gap_pt = LIST_SECTION_END_GAP_PT if is_last else ENTRY_GAP_PT
            gap = compute_gap(base_gap_pt, config_override)
            if gap:
                entry += "\n" + gap

            parts.append(entry)
        except KeyError as e:
            raise ValueError(f"Missing key in experience data: {e}")

    return "\n".join(parts)
