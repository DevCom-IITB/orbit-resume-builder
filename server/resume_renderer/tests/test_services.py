from resume_renderer.services.markdown_parser import MarkdownParser

markdown_parser = MarkdownParser()


def test_markdown_parser():
    """Test the markdown parser with various inputs"""
    text = "This is **bold** and this is *italic*."
    excepted = "This is \\textbf{bold} and this is \\textit{italic}."

    text2 = "This is a _underline_ text."
    expected2 = "This is a \\underline{underline} text."

    assert markdown_parser.parse(text) == excepted
    assert markdown_parser.parse(text2) == expected2
