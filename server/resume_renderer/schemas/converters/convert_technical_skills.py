"""
Converts technical skills JSON into IITB-format LaTeX.

Schema: list of {category, skills: [str]}
"""

from ...services.json_sanitizer import sanitize_text
from ...services.markdown_parser import MARKDOWN_PARSER


def convert_technical_skills(skills_data: list) -> str:
    if not isinstance(skills_data, list):
        raise ValueError("Input must be a list of skill categories.")
    if not skills_data:
        return ""

    rows = []
    for item in skills_data:
        category = MARKDOWN_PARSER.parse(sanitize_text(item.get("category", "")))
        skills = item.get("skills", [])
        if not isinstance(skills, list):
            raise ValueError("'skills' must be a list.")
        skills_str = ", ".join(
            MARKDOWN_PARSER.parse(sanitize_text(s)) for s in skills if isinstance(s, str)
        )
        rows.append(rf"    \textbf{{{category}}} & {skills_str} \\")

    parts = [
        r"""\section*{\color{myblue}{\large TECHNICAL SKILLS}\xfilll[0pt]{0.5pt}}
\vspace{-10pt}
\renewcommand{\arraystretch}{1.1}
\begin{tabular}{p{4cm} p{12.9cm}}"""
    ]
    parts.extend(rows)
    parts.append(r"\end{tabular}")
    return "\n".join(parts)
