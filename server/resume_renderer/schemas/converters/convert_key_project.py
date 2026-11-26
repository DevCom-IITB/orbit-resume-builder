"""
Converts key project JSON into IITB-format LaTeX.

Schema: title, organization, summary, timeline, bullets
"""

from ...services.bullet_probe import annotate_bullet, annotate_summary
from ...services.json_sanitizer import sanitize_text
from ...services.markdown_parser import MARKDOWN_PARSER
from .iitb_layout import ENTRY_GAP_PT, LIST_SECTION_END_GAP_PT, compute_gap


def convert_key_project(projects: list, config_override: dict = None) -> str:
    if not isinstance(projects, list):
        raise ValueError("Input must be a list of project entries.")
    if not projects:
        return ""

    parts = [
        r"""\section*{\color{myblue}{\large KEY PROJECTS}\xfilll[0pt]{0.5pt}}
\vspace{-8pt}"""
    ]

    total = len(projects)
    for idx, proj in enumerate(projects):
        try:
            title = MARKDOWN_PARSER.parse(sanitize_text(proj["title"]))
            organization = MARKDOWN_PARSER.parse(sanitize_text(proj.get("organization", "")))
            timeline = MARKDOWN_PARSER.parse(sanitize_text(proj.get("timeline", "")))
            raw_summary = proj.get("summary", "")
            summary = annotate_summary(
                raw_summary,
                MARKDOWN_PARSER.parse(sanitize_text(raw_summary)),
                config_override,
            )
            raw_bullets = proj.get("bullets", [])
            if not isinstance(raw_bullets, list):
                raise ValueError("'bullets' must be a list.")
            bullets = [b for b in raw_bullets if isinstance(b, str) and b.strip()]

            org_part = rf" $\vert$\ \it\small{{{organization}}}" if organization else ""
            time_part = rf"\hfill{{\small\it({timeline})}}" if timeline else ""

            entry = rf"""
\begin{{localsize}}{{11}}
\noindent{{\bf {title}}}{org_part}{time_part}\par
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
                entry += "\n" + r"\begin{itemize}[label=\textcolor{myblue}{\textbullet}, itemsep = -0.75 mm, leftmargin=*]"
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
            raise ValueError(f"Missing key in project data: {e}")

    return "\n".join(parts)
