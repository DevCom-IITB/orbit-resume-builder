"""Convert header JSON into LaTeX."""

from .json_sanitizer import sanitize_text


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
    try:
        name = sanitize_text(header["name"])
        edu = sanitize_text(header["edu"])
        contact = header["contact"]
        email = sanitize_text(contact["email"])
        phone = sanitize_text(contact["phone"])
        linkedin = sanitize_text(contact["linkedin"])
        github = sanitize_text(contact["github"])

        return (
            TEMPLATE.replace("__NAME__", name)
            .replace("__EDU__", edu)
            .replace("__EMAIL__", email)
            .replace("__PHONE__", phone)
            .replace("__LINKEDIN__", linkedin)
            .replace("__GITHUB__", github)
        )
    except KeyError as e:
        raise ValueError(f"Missing key in header data: {e}")
    except ValueError as e:
        raise ValueError(f"Invalid data in header: {e}")
