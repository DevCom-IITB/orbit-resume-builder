"""
Converts technical skills JSON into LaTeX tabular rows.

Expected input:
[
    {"category": "Programming", "skills": ["Python", "C++", "JavaScript"]},
    {"category": "AI and ML", "skills": ["TensorFlow", "PyTorch"]}
]
"""

from ...services.json_sanitizer import sanitize_text
from ...services.markdown_parser import MARKDOWN_PARSER


def convert_technical_skills(skills: list) -> str:
    """Convert technical skills JSON into LaTeX TECHNICAL SKILLS section.

    Args:
        skills: list of dicts with keys `category` and `skills` (list of strings).

    Returns:
        LaTeX string for the TECHNICAL SKILLS section.
    """
    if not isinstance(skills, list):
        raise ValueError("Input must be a list of technical skill sections.")

    if not skills:
        return ""

    parts: list[str] = [
        r"""
%============================================================================
%   Technical Skills SECTION
%----------------------------------------------------------------------------
\section{\textbf{Technical Skills}}

\renewcommand{\arraystretch}{1.5}
\begin{tabularx}{\linewidth}{@{}p{4.5cm}X@{}}
"""
    ]

    for item in skills:
        try:
            if not isinstance(item, dict):
                raise ValueError("Each skill entry must be a dictionary.")

            category = MARKDOWN_PARSER.parse(sanitize_text(item["category"]))

            skill_list = item.get("skills", [])

            if not isinstance(skill_list, list):
                raise ValueError("'skills' must be a list.")

            parsed_skills = []

            for skill in skill_list:
                if not isinstance(skill, str):
                    raise ValueError("Each skill must be a string.")

                parsed_skills.append(MARKDOWN_PARSER.parse(sanitize_text(skill)))

            skill_text = ", ".join(parsed_skills)

            parts.append(rf"\textbf{{{category}}} & {skill_text} \\")

        except KeyError as e:
            raise ValueError(f"Missing key in technical skills item: {e}")

        except ValueError as e:
            raise ValueError(f"Invalid technical skills data: {e}")

    parts.extend(
        [
            r"\end{tabularx}",
            r"%----------------------------------------------------------------------------",
            r"%============================================================================",
        ]
    )

    return "\n".join(parts)
