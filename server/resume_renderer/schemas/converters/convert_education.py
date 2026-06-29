"""
Converts education JSON into IITB-format LaTeX tabular.

New schema fields: examination, university, institute, year, cpi, note (optional)
"""

from ...services.json_sanitizer import sanitize_text
from ...services.markdown_parser import MARKDOWN_PARSER


def convert_education(education: list) -> str:
    if not isinstance(education, list):
        raise ValueError("Input must be a list of education entries.")
    if not education:
        return ""

    rows = []
    note_text = ""
    for edu in education:
        try:
            examination = MARKDOWN_PARSER.parse(sanitize_text(edu.get("examination", "")))
            university = MARKDOWN_PARSER.parse(sanitize_text(edu.get("university", "")))
            institute = MARKDOWN_PARSER.parse(sanitize_text(edu.get("institute", "")))
            year = MARKDOWN_PARSER.parse(sanitize_text(edu.get("year", "")))
            cpi = MARKDOWN_PARSER.parse(sanitize_text(edu.get("cpi", "")))
            note = edu.get("note", "")
            if note:
                note_text = MARKDOWN_PARSER.parse(sanitize_text(note))
            rows.append(rf"    {examination} & {university} & {institute} & {year} & {cpi} \\")
        except KeyError as e:
            raise ValueError(f"Missing key in education entry: {e}")

    parts = [
        r"""
\noindent
\begin{tabularx}{\textwidth}{p{3.2cm} p{4cm} p{5.5cm} p{2cm} p{2cm}}
    \midrule
    \textbf{Examination} & \textbf{University} & \textbf{Institute} & \textbf{Year} & \textbf{CPI} \\
    \midrule
"""
    ]
    parts.append("\n".join(rows))
    parts.append(r"""    \bottomrule
\end{tabularx}""")

    if note_text:
        parts.append(rf"""
\vspace{{10pt}}
\noindent {note_text} \\
\vspace{{-18pt}}""")

    return "\n".join(parts)
