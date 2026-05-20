"""
Converts courses undertaken JSON into LaTeX tabular rows.

Expected input:
[
    {"category": "AI and Data Science", "courses": ["Programming for Data Science", "Digital Image Processing"]},
    {"category": "Mathematics", "courses": ["Calculus", "Linear Algebra"]}
]

If an item has a `note` key, it will be rendered as a separate italic row (matching the project's sample).
"""

from ...services.json_sanitizer import sanitize_text
from ...services.markdown_parser import MARKDOWN_PARSER


def convert_courses(courses: list) -> str:
    """Convert courses JSON into LaTeX tabular section.

    Args:
        courses: list of dicts with keys `category`, `courses` (list of strings), optional `note`.

    Returns:
        LaTeX string for the COURSES UNDERTAKEN section.
    """
    if not isinstance(courses, list):
        raise ValueError("Input must be a list of course sections.")

    if not courses:
        return ""

    parts: list[str] = [
        r"""
%============================================================================
\section*{\color{myblue}{\large COURSES UNDERTAKEN}\xfilll[0pt]{0.5pt}}

\begin{tabularx}{\linewidth}{@{}p{3.8cm}X@{}}
"""
    ]

    for item in courses:
        try:
            category = MARKDOWN_PARSER.parse(sanitize_text(item["category"]))

            course_list = item.get("courses", [])
            if not isinstance(course_list, list):
                raise ValueError("'courses' must be a list.")

            parsed_courses = [
                MARKDOWN_PARSER.parse(sanitize_text(course)) for course in course_list
            ]

            course_text = ", ".join(parsed_courses)

            parts.append(rf"\textbf{{{category}}} & {course_text} \\")

            note = item.get("note")
            if note:
                note_text = MARKDOWN_PARSER.parse(sanitize_text(note))

                parts.append(rf"& \small\itshape {note_text} \\")

        except KeyError as e:
            raise ValueError(f"Missing key in courses item: {e}")

    parts.extend(
        [
            r"\end{tabularx}",
            r"%----------------------------------------------------------------------------",
            r"%============================================================================",
        ]
    )

    return "\n".join(parts)
