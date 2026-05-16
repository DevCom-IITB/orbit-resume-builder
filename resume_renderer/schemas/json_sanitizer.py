import re


LATEX_COMMAND_PATTERN = re.compile(r"\\[a-zA-Z]+")

SPECIAL_CHARACTERS = {
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def validate_no_latex(text: str) -> None:
    if LATEX_COMMAND_PATTERN.search(text):
        raise ValueError("Raw LaTeX commands are not allowed.")


def escape_latex(text: str) -> str:
    for char, escaped in SPECIAL_CHARACTERS.items():
        text = text.replace(char, escaped)
    return text


def sanitize_text(text: str) -> str:
    validate_no_latex(text)
    return escape_latex(text)
