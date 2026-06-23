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
\section{\textbf{Education}}

\noindent
{\setlength{\tabcolsep}{4pt}
\begin{tabularx}{\textwidth}{@{}L{3.0cm} L{3.6cm} L{6.5cm} C{2cm} C{1.9cm}@{}}
    \toprule
    \textbf{Examination} & \textbf{University} & \textbf{Institute} & \textbf{Year} & \textbf{CPI / \%} \\
    \midrule
"""
    ]

    rows = []
    for edu in education:
        try:
            degree = MARKDOWN_PARSER.parse(sanitize_text(edu["degree"]))
            institution = MARKDOWN_PARSER.parse(sanitize_text(edu["institution"]))
            cpi = MARKDOWN_PARSER.parse(sanitize_text(edu["cpi"]))
            year = MARKDOWN_PARSER.parse(sanitize_text(edu["year"]))

            # Try to split into university/board and institute
            inst_parts = [part.strip() for part in institution.split("|", 1)]
            if len(inst_parts) == 2:
                univ, inst = inst_parts[0], inst_parts[1]
            else:
                inst_parts = [part.strip() for part in institution.split(",", 1)]
                if len(inst_parts) == 2:
                    univ, inst = inst_parts[0], inst_parts[1]
                else:
                    univ, inst = institution, institution

            rows.append(
                rf"{degree} & {univ} & {inst} & {year} & {cpi} \\"
            )

        except KeyError as e:
            raise ValueError(f"Missing key in education entry: {e}")

    parts.append(f"\n    \\cmidrule(lr){{1-5}}\n    ".join(rows))
    parts.extend(
        [
            r"    \bottomrule",
            r"\end{tabularx}",
            r"}",
            r"%----------------------------------------------------------------------------",
            r"%============================================================================",
        ]
    )

    return "\n".join(parts)
