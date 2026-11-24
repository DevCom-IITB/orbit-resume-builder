"""
Converts positions of responsibility JSON into IITB-format LaTeX.

Schema: role, organization, duration, summary, bullets
"""

from ...services.bullet_probe import annotate_bullet, annotate_summary
from ...services.json_sanitizer import sanitize_text
from ...services.markdown_parser import MARKDOWN_PARSER
from .iitb_layout import ENTRY_GAP_PT, LIST_SECTION_END_GAP_PT, compute_gap


def convert_pors(positions: list, config_override: dict = None) -> str:
    if not isinstance(positions, list):
        raise ValueError("Input must be a list of position entries.")
    if not positions:
        return ""

    parts = [
        r"""\section*{\color{myblue}{\large POSITIONS OF RESPONSIBILITY}\xfilll[0pt]{0.5pt}}
\vspace{-8pt}"""
    ]

    total = len(positions)
    for idx, pos in enumerate(positions):
        try:
            role = MARKDOWN_PARSER.parse(sanitize_text(pos["role"]))
            organization = MARKDOWN_PARSER.parse(sanitize_text(pos["organization"]))
            duration = MARKDOWN_PARSER.parse(sanitize_text(pos.get("duration", "")))
            raw_summary = pos.get("summary", "")
            summary = annotate_summary(
                raw_summary,
                MARKDOWN_PARSER.parse(sanitize_text(raw_summary)),
                config_override,
            ) if raw_summary else ""
            raw_bullets = pos.get("bullets", [])
            if not isinstance(raw_bullets, list):
                raise ValueError("'bullets' must be a list.")
            bullets = [b for b in raw_bullets if isinstance(b, str) and b.strip()]

            org_part = rf" $\vert$\ \it\small{{{organization}}}" if organization else ""
            dur_part = rf"\hfill{{\small\it({duration})}}" if duration else ""

            entry = rf"""
\begin{{localsize}}{{11}}
\noindent{{\bf {role}}}{org_part}{dur_part}\par
\vspace{{-7pt}}
\noindent\rule{{\linewidth}}{{0.4pt}}\par
\end{{localsize}}"""

            if summary:
                if bullets:
                    entry += rf"""
\vspace{{-0.5pt}}
\noindent{{\it {summary}}}\par
\vspace{{-8pt}}"""
                else:
                    entry += rf"""
\vspace{{-0.5pt}}
\noindent{{\it {summary}}}\par"""
            else:
                entry += r"""
\vspace{-11pt}"""

            if bullets:
                entry += "\n" + r"\begin{itemize}[label=\textcolor{myblue}{\textbullet}, itemsep = -0.80 mm, leftmargin=*]"
                for bullet in bullets:
                    b = annotate_bullet(bullet, MARKDOWN_PARSER.parse(sanitize_text(bullet)), config_override, protect_item=True)
                    entry += f"\n    \\item {b}"
                entry += "\n" + r"\end{itemize}"

            is_last = (idx == total - 1)
            base_gap_pt = LIST_SECTION_END_GAP_PT if is_last else ENTRY_GAP_PT
            gap = compute_gap(base_gap_pt, config_override)
            if gap:
                entry += "\n" + gap

            parts.append(entry)
        except KeyError as e:
            raise ValueError(f"Missing key in position data: {e}")

    return "\n".join(parts)
