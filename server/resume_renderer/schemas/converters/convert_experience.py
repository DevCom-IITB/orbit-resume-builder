"""Convert experience JSON into LaTeX."""

from ...services.json_sanitizer import sanitize_text
from ...services.markdown_parser import MarkdownParser


def convert_experience(experiences: list) -> str:
    """Convert experience JSON into LaTeX.

    Args:
        experiences: A list of dictionaries, each containing 'title', 'organisation', 'location',
                        'timeline', and 'bullets'.

    Returns:
        A string containing the LaTeX code for the experience section of the resume.

    Raises:
        ValueError: If the input data is not in the expected format.
    """
    parts: list[str] = []
    parts.append(r"\section{Professional Experience}")
    markdown_parser = MarkdownParser()

    if not isinstance(experiences, list):
        raise ValueError("Input must be a list of experiences.")

    for exp in experiences:
        try:
            title = markdown_parser.parse(sanitize_text(exp["title"]))
            organisation = markdown_parser.parse(sanitize_text(exp["organisation"]))
            location = markdown_parser.parse(sanitize_text(exp["location"]))
            timeline = markdown_parser.parse(sanitize_text(exp["timeline"]))
            bullets = exp["bullets"]

            parts.append(
                rf"\entry{{{title}}}{{{organisation}}}{{{location}}}{{{timeline}}}"
            )
            parts.append(r"\begin{itemize}")
            for bullet in bullets:
                parts.append(rf"  \item {markdown_parser.parse(sanitize_text(bullet))}")
            parts.append(r"\end{itemize}")
            parts.append(r"\vspace{4pt}")
        except KeyError as e:
            raise ValueError(f"Missing key in experience data: {e}")
        except ValueError as e:
            raise ValueError(f"Invalid data in experience: {e}")

    if parts and parts[-1] == r"\vspace{4pt}":
        parts.pop()

    return "\n".join(parts)
