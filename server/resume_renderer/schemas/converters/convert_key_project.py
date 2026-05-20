"""Convert key project JSON into LaTeX."""

from ...services.json_sanitizer import sanitize_text
from ...services.markdown_parser import MarkdownParser


def convert_key_project(projects: list) -> str:
    """Convert key project JSON into LaTeX.

    Args:
        projects: A list of dictionaries, each containing 'title', 'guide', 'location',
                        'timeline', and 'bullets'.

    Returns:
        A string containing the LaTeX code for the key projects section of the resume.

    Raises:
        ValueError: If the input data is not in the expected format.
    """
    parts: list[str] = []
    parts.append(r"\section{Key Projects}")
    markdown_parser = MarkdownParser()

    if not isinstance(projects, list):
        raise ValueError("Input must be a list of projects.")

    for proj in projects:
        try:
            title = markdown_parser.parse(sanitize_text(proj["title"]))
            guide = markdown_parser.parse(sanitize_text(proj["guide"]))
            location = markdown_parser.parse(sanitize_text(proj["location"]))
            timeline = markdown_parser.parse(sanitize_text(proj["timeline"]))
            bullets = proj["bullets"]

            parts.append(rf"\entry{{{title}}}{{{guide}}}{{{location}}}{{{timeline}}}")
            parts.append(r"\begin{itemize}")
            for bullet in bullets:
                parts.append(rf"\item {markdown_parser.parse(sanitize_text(bullet))}")
            parts.append(r"\end{itemize}")
            parts.append(r"\vspace{4pt}")
        except KeyError as e:
            raise ValueError(f"Missing key in project data: {e}")
        except ValueError as e:
            raise ValueError(f"Invalid data in project: {e}")

    if parts and parts[-1] == r"\vspace{4pt}":
        parts.pop()

    return "\n".join(parts)
