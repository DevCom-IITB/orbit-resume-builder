from resume_renderer.services.markdown_parser import MARKDOWN_PARSER
from resume_renderer.services import renderer


def test_markdown_parser():
    """Test the markdown parser with various inputs"""
    text = "This is **bold** and this is *italic*."
    excepted = "This is \\textbf{bold} and this is \\textit{italic}."

    text2 = "This is a _underline_ text."
    expected2 = "This is a \\underline{underline} text."

    assert MARKDOWN_PARSER.parse(text) == excepted
    assert MARKDOWN_PARSER.parse(text2) == expected2


def test_renderer_template_has_section_spacing_directive():
    assert "\\renewcommand{\\section}" in renderer.TEMPLATE


def test_ensure_image_exists_force_rebuild_removes_image(monkeypatch):
    class FakeImages:
        def __init__(self):
            self.remove_called = False
            self.get_called = False

        def remove(self, _name, force=False):
            self.remove_called = force

        def get(self, _name):
            self.get_called = True

    class FakeClient:
        def __init__(self):
            self.images = FakeImages()

    fake_client = FakeClient()
    monkeypatch.setattr(renderer, "client", fake_client)

    renderer.ensure_image_exists(force_rebuild=True)

    assert fake_client.images.remove_called is True
    assert fake_client.images.get_called is True
