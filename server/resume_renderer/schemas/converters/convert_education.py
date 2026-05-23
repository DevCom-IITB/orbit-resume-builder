"""
Converts education JSON data into LaTeX format for the resume.

example json:
[
    {
        "degree": "Bachelor of Technology in Computer Science and Engineering",
        "institution": "Indian Institute of Technology, Bombay",
        "cpi": "9.2",
        "year": "2020 - 2024"
    },
    {
        "degree": "High School",
        "institution": "ABC High School",
        "cpi": "95%",
        "year": "2018 - 2020"
    }
]

"""

from ...services.json_sanitizer import sanitize_text
from ...services.markdown_parser import MARKDOWN_PARSER


def convert_education(education: list) -> str:
    """Convert education JSON into a LaTeX table.

    Args:
        education: A list of dictionaries, each containing 'degree', 'institution', 'cpi', and 'year'.

    Returns:
        A string containing the LaTeX code for the education section of the resume.

    Raises:
        ValueError: If the input data is not in the expected format.
    """
    if not isinstance(education, list):
        raise ValueError("Input must be a list of education entries.")

    if not education:
        return ""

    parts: list[str] = [
        r"""
%============================================================================
%   Education SECTION
%----------------------------------------------------------------------------
\section*{\color{myblue}{\large EDUCATION}\xfilll[0pt]{0.5pt}}

\noindent
\begin{tabularx}{\linewidth}{@{}lXrr@{}}
\textbf{Degree} &
\textbf{Institution} &
\textbf{CPI / \%} &
\textbf{Year} \\[2pt]
\hline
\\[-5pt]
"""
    ]

    for edu in education:
        try:
            degree = MARKDOWN_PARSER.parse(sanitize_text(edu["degree"]))

            institution = MARKDOWN_PARSER.parse(sanitize_text(edu["institution"]))

            cpi = MARKDOWN_PARSER.parse(sanitize_text(edu["cpi"]))

            year = MARKDOWN_PARSER.parse(sanitize_text(edu["year"]))

            parts.append(
                rf"{degree} & "
                rf"{institution} & "
                rf"{cpi} & "
                rf"{year} \\"
            )

        except KeyError as e:
            raise ValueError(f"Missing key in education entry: {e}")

    parts.extend(
        [
            r"\end{tabularx}",
            r"%----------------------------------------------------------------------------",
            r"%============================================================================",
        ]
    )

    return "\n".join(parts)
