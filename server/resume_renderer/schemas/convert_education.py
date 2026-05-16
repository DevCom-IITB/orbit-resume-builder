"""Convert education JSON into LaTeX."""

from .json_sanitizer import sanitize_text


def convert_education(education: list) -> str:
    """Convert education JSON into a LaTeX table.
    
    Args:
        education: A list of dictionaries, each containing 'degree', 'institution', 'cpi', and 'year'.
        
    Returns:
        A string containing the LaTeX code for the education section of the resume.
        
    Raises:
        ValueError: If the input data is not in the expected format.
    """
    parts: list[str] = []
    parts.append(r"\section{Education}")
    parts.append(r"\noindent")
    parts.append(
        r"\begin{tabularx}{\linewidth}{@{} l X r r @{}} \textbf{Degree} & \textbf{Institution} & \textbf{CPI / \%} & \textbf{Year} \\[2pt] \hline\\[-6pt]"
    )

    if not isinstance(education, list):
        raise ValueError("Input must be a list of education entries.")

    for edu in education:
        try:
            degree = sanitize_text(edu["degree"])
            institution = sanitize_text(edu["institution"])
            cpi = sanitize_text(edu["cpi"])
            year = sanitize_text(edu["year"])

            parts.append(rf"{degree} & {institution} & {cpi} & {year} \\")
        except KeyError as e:
            raise ValueError(f"Missing key in education entry: {e}")

    parts.append(r"\end{tabularx}")
    return "\n".join(parts)
