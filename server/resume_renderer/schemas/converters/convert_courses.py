"""
Converts courses undertaken JSON into IITB-format LaTeX.

Schema: list of {category, courses: [str], note?: str}
"""

from ...services.json_sanitizer import sanitize_text
from ...services.markdown_parser import MARKDOWN_PARSER


def convert_courses(courses_data: list) -> str:
    if not isinstance(courses_data, list):
        raise ValueError("Input must be a list of course categories.")
    if not courses_data:
        return ""

    rows = []
    for item in courses_data:
        category = MARKDOWN_PARSER.parse(sanitize_text(item.get("category", "")))
        courses = item.get("courses", [])
        if not isinstance(courses, list):
            raise ValueError("'courses' must be a list.")
        courses_str = ", ".join(
            MARKDOWN_PARSER.parse(sanitize_text(c)) for c in courses if isinstance(c, str)
        )
        note = item.get("note", "")
        if note:
            note_clean = sanitize_text(note)
            courses_str += rf" \textit{{{note_clean}}}"
        rows.append(rf"    \textbf{{{category}}} & {courses_str} \\")

    parts = [
        r"""\section*{\color{myblue}{\large COURSES UNDERTAKEN}\xfilll[0pt]{0.5pt}}
\vspace{-8pt}
\begin{tabular}{p{4cm} p{12.9cm}}"""
    ]
    parts.extend(rows)
    parts.append(r"\end{tabular}")
    return "\n".join(parts)
