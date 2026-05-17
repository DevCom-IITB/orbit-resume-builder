"""
Parses markdown text into LaTeX
"""

import re


class MarkdownParser:
    def __init__(self):
        self.bold_pattern = re.compile(r"\*\*(.*?)\*\*")
        self.italic_pattern = re.compile(r"\*(.*?)\*")
        self.underline_pattern = re.compile(r"_(.*?)_")

    def parse(self, text: str) -> str:
        r"""Parse markdown syntax into LaTeX commands.

        Converts:
        - **text** -> \textbf{text}
        - *text* -> \textit{text}
        - _text_ -> \underline{text}

        Args:
            text: The text with markdown syntax to parse.

        Returns:
            The text with markdown converted to LaTeX.
        """
        # Bold must be processed first to avoid conflicts with italic
        text = self.bold_pattern.sub(r"\\textbf{\1}", text)
        # Italic after bold
        text = self.italic_pattern.sub(r"\\textit{\1}", text)
        # Underline last
        text = self.underline_pattern.sub(r"\\underline{\1}", text)
        return text
