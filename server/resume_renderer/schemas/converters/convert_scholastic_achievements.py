"""
Converts scholastic achievements JSON into IITB-format LaTeX.

New schema: list of {text, year?}
Old schema (backward compat): list of strings
"""

from ...services.json_sanitizer import sanitize_text
from ...services.markdown_parser import MARKDOWN_PARSER


def convert_scholastic_achievements(achievements: list) -> str:
    if not isinstance(achievements, list):
        raise ValueError("Input must be a list of achievements.")
    if not achievements:
        return ""

    parts = [
        r"""\section*{\color{myblue}{\large SCHOLASTIC ACHIEVEMENTS}\xfilll[0pt]{0.5pt}}
\vspace{-8pt}
\begin{itemize}[label=\textcolor{myblue}{\textbullet},itemsep = -0.75 mm, leftmargin=*]"""
    ]

    for ach in achievements:
        if isinstance(ach, str):
            text = MARKDOWN_PARSER.parse(sanitize_text(ach))
            parts.append(rf"    \item {text}")
        elif isinstance(ach, dict):
            text = MARKDOWN_PARSER.parse(sanitize_text(ach.get("text", "")))
            year = ach.get("year", "")
            if year:
                year_clean = sanitize_text(year)
                parts.append(rf"    \item {text} \hfill{{\small({year_clean})}}")
            else:
                parts.append(rf"    \item {text}")
        else:
            raise ValueError(f"Each achievement must be a string or dict, got: {type(ach)}")

    parts.append(r"\end{itemize}")
    return "\n".join(parts)
