"""
Converts header JSON data into IITB-format LaTeX.

New schema fields: name, roll_no, department, degree, institution, gender, email, phone
"""

from ...services.json_sanitizer import sanitize_text
from ...services.markdown_parser import MARKDOWN_PARSER


def convert_header(header: dict) -> str:
    if not isinstance(header, dict):
        raise ValueError("Header must be a dictionary.")

    try:
        name = MARKDOWN_PARSER.parse(sanitize_text(header["name"]))
        roll_no = MARKDOWN_PARSER.parse(sanitize_text(header.get("roll_no", "")))
        department = MARKDOWN_PARSER.parse(sanitize_text(header.get("department", "")))
        degree = MARKDOWN_PARSER.parse(sanitize_text(header.get("degree", "")))
        institution = MARKDOWN_PARSER.parse(
            sanitize_text(header.get("institution", "Indian Institute of Technology Bombay"))
        )
        gender = MARKDOWN_PARSER.parse(sanitize_text(header.get("gender", "")))
        email = sanitize_text(header.get("email", ""))
        phone = sanitize_text(header.get("phone", ""))

        return rf"""
\noindent
\begin{{minipage}}{{0.15\textwidth}}
    \includegraphics[width=\linewidth]{{iitb-logo.png}}
\end{{minipage}}%
\hspace{{1cm}}
\begin{{minipage}}{{0.8\textwidth}}
    \renewcommand{{\arraystretch}}{{1.25}}
    \begin{{tabular}}{{@{{}}p{{7.5cm}} p{{5cm}}@{{}}}}
        \large{{\textbf{{{name}}}}} & \textbf{{{roll_no}}} \\
        \textbf{{{department}}} & \textbf{{{degree}}} \\
        \textbf{{{institution}}} & \textbf{{Gender: {gender}}} \\
        \href{{mailto:{email}}}{{{email}}} & \textbf{{{phone}}} \\
    \end{{tabular}}
\end{{minipage}}
"""
    except KeyError as e:
        raise ValueError(f"Missing key in header data: {e}")
