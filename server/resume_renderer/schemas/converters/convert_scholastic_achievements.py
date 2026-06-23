"""
Converts scholastic achievements JSON into LaTeX itemize section.

Expected input: list of strings, each an achievement.
"""

from ...services.json_sanitizer import sanitize_text
from ...services.markdown_parser import MARKDOWN_PARSER


def convert_scholastic_achievements(achievements: list) -> str:
    """Convert scholastic achievements list into LaTeX.

    Args:
        achievements: list of strings

    Returns:
        LaTeX string for SCHOLASTIC ACHIEVEMENTS section.
    """
    if not isinstance(achievements, list):
        raise ValueError("Input must be a list of achievements.")

    if not achievements:
        return ""

    import re
    def format_year_hfill(text: str) -> str:
        return re.sub(r"\s+\[([^\]]+)\]\s*$", r" \\hfill[\1]", text)

    parts: list[str] = [
        r"""
%============================================================================
%   Scholastic Achievements SECTION
%----------------------------------------------------------------------------
\section{\textbf{Scholastic Achievements}}

\begin{itemize}
"""
    ]

    for ach in achievements:
        if not isinstance(ach, str):
            raise ValueError("Each achievement must be a string.")

        text = MARKDOWN_PARSER.parse(sanitize_text(ach))
        text = format_year_hfill(text)

        parts.append(rf"    \item {text}")

    parts.extend(
        [
            r"\end{itemize}",
            r"%----------------------------------------------------------------------------",
            r"%============================================================================",
        ]
    )

    return "\n".join(parts)
