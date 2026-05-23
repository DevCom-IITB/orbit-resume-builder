"""
To convert the header json data into latex

example input:
{
    "name" : "Siddhant Sharma",
    "edu" : "B.Tech. in Aerospace Engineering",
    "contact" : {
        "email" : "sid@sidshr.in",
        "phone" : "+91 12345 67890",
        "linkedin" : "1783717828",
        "github" : "siddhantshr"
    }
}
"""

from ...services.json_sanitizer import sanitize_text
from ...services.markdown_parser import MARKDOWN_PARSER


TEMPLATE = r"""
\begin{center}
  {\LARGE\bfseries\color{iitbblue} __NAME__}\\[4pt]
  __EDU__ \quad|\quad
  Indian Institute of Technology Bombay\\[3pt]
    Email: \href{mailto:__EMAIL__}{__EMAIL__} \quad
    Phone: __PHONE__ \quad
    LinkedIn: \href{https://linkedin.com/in/__LINKEDIN__}{linkedin.com/in/__LINKEDIN__} \quad
    GitHub: \href{https://github.com/__GITHUB__}{github.com/__GITHUB__}
\end{center}
"""


def convert_header(header: dict) -> str:
    """Convert header JSON into LaTeX.

    Args:
        header: A dictionary containing the header information.

    Returns:
        A string containing the LaTeX code for the header section of the resume.

    Raises:
        ValueError: If the input data is not in the expected format.
    """
    if not isinstance(header, dict):
        raise ValueError("Header must be a dictionary.")

    try:
        name = MARKDOWN_PARSER.parse(sanitize_text(header["name"]))

        edu = MARKDOWN_PARSER.parse(sanitize_text(header["edu"]))

        contact = header.get("contact", {})
        if not isinstance(contact, dict):
            raise ValueError("'contact' must be a dictionary.")

        email = MARKDOWN_PARSER.parse(sanitize_text(contact.get("email", "")))

        phone = MARKDOWN_PARSER.parse(sanitize_text(contact.get("phone", "")))

        linkedin = MARKDOWN_PARSER.parse(sanitize_text(contact.get("linkedin", "")))

        github = MARKDOWN_PARSER.parse(sanitize_text(contact.get("github", "")))

        replacements = {
            "__NAME__": name,
            "__EDU__": edu,
            "__EMAIL__": email,
            "__PHONE__": phone,
            "__LINKEDIN__": linkedin,
            "__GITHUB__": github,
        }

        latex = TEMPLATE
        for key, value in replacements.items():
            latex = latex.replace(key, value)

        return latex

    except KeyError as e:
        raise ValueError(f"Missing key in header data: {e}")

    except ValueError as e:
        raise ValueError(f"Invalid data in header: {e}")
