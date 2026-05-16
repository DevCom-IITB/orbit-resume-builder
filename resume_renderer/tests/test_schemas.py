from resume_renderer.schemas.convert_education import convert_education
from resume_renderer.schemas.convert_experience import convert_experience
from resume_renderer.schemas.convert_header import convert_header
from resume_renderer.schemas.convert_key_project import convert_key_project
from resume_renderer.schemas.json_sanitizer import sanitize_text


def test_sanitize_text_escapes_special_chars():
    """Test that sanitize_text properly escapes LaTeX special characters."""
    text = "A & B_#"
    assert sanitize_text(text) == "A \\& B\\_\\#"


def test_sanitize_text_rejects_commands():
    """Test that sanitize_text rejects raw LaTeX commands."""
    try:
        sanitize_text("\\\\input{evil}")
    except ValueError as exc:
        assert "Raw LaTeX commands" in str(exc)
    else:
        raise AssertionError("Expected sanitize_text to reject LaTeX commands")


def test_convert_header_formats_contacts():
    """Test that convert_header correctly formats contact information."""
    header = {
        "name": "Jane Doe",
        "edu": "B.Tech",
        "contact": {
            "email": "jane@example.com",
            "phone": "+1 555 000",
            "linkedin": "jane-doe",
            "github": "janedoe",
        },
    }
    latex = convert_header(header)
    assert "Jane Doe" in latex
    assert "mailto:jane@example.com" in latex
    assert "linkedin.com/in/jane-doe" in latex
    assert "github.com/janedoe" in latex


def test_convert_education_builds_table():
    """Test that convert_education builds a LaTeX table with the correct structure."""
    education = [
        {
            "degree": "B.Tech",
            "institution": "IIT",
            "cpi": "9.1",
            "year": "2021-2025",
        }
    ]
    latex = convert_education(education)
    assert "\\section{Education}" in latex
    assert "B.Tech" in latex
    assert "IIT" in latex


def test_convert_experience_includes_items():
    """Test that convert_experience includes bullet points in the output."""
    experiences = [
        {
            "title": "Intern",
            "organisation": "ACME",
            "location": "Remote",
            "timeline": "2024",
            "bullets": ["Did work", "Wrote tests"],
        }
    ]
    latex = convert_experience(experiences)
    assert "\\section{Professional Experience}" in latex
    assert "\\begin{itemize}" in latex
    assert "Did work" in latex
    assert "Wrote tests" in latex

def test_convert_key_project_includes_items():
    """Test that convert_key_project includes bullet points in the output."""
    projects = [
        {
            "title": "Project X",
            "guide": "Dr. Y",
            "location": "Mumbai",
            "timeline": "2023",
            "bullets": ["Built thing"],
        }
    ]
    latex = convert_key_project(projects)
    assert "\\section{Key Projects}" in latex
    assert "Built thing" in latex
