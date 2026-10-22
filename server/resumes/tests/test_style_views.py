"""
Tests for GET/PATCH /api/resumes/<id>/style/
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from resumes.models import Resume, ResumeTemplate, VisualTheme


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def api_client():
    return APIClient()


@pytest.fixture()
def user(db):
    return get_user_model().objects.create_user(username="styleuser", password="pass")


@pytest.fixture()
def other_user(db):
    return get_user_model().objects.create_user(username="otheruser", password="pass")


@pytest.fixture()
def theme(db):
    return VisualTheme.objects.create(
        key="sv-theme",
        display_name="Style View Theme",
        compatible_families=["iitb"],
        converter_set_key="iitb-classic",
        latex_preamble=(
            "% renderer-v2\n"
            "__FONT_SETUP__\n"
            "\\definecolor{myblue}{HTML}{__ACCENT_HEX__}\n"
            "__SPACING_SETUP__\\begin{document}\n"
            "__CONTENT__\n"
            "\\end{document}"
        ),
    )


@pytest.fixture()
def template(db, theme):
    t = ResumeTemplate.objects.create(
        key="sv-template",
        display_name="Style View Template",
        family="iitb",
        domain="general",
        template_config={
            "font_options": ["lmodern", "times", "charter"],
            "font_default": "lmodern",
            "accent_options": ["#4B41C8", "#1A6B3C"],
            "accent_default": "#4B41C8",
        },
    )
    t.available_themes.add(theme)
    return t


@pytest.fixture()
def resume(db, user, template, theme):
    return Resume.objects.create(
        owner=user,
        title="Style Test Resume",
        template=template,
        visual_theme=theme,
        config_override={},
    )


# ---------------------------------------------------------------------------
# GET /api/resumes/<id>/style/
# ---------------------------------------------------------------------------

def test_get_style_returns_correct_shape(api_client, user, resume):
    api_client.force_authenticate(user=user)
    response = api_client.get(f"/api/resumes/{resume.id}/style/")
    assert response.status_code == 200
    data = response.json()
    assert "style" in data
    assert "options" in data
    assert "font" in data["style"]
    assert "accent" in data["style"]
    assert "line_spacing" in data["style"]
    assert "word_spacing" in data["style"]
    assert "fonts" in data["options"]
    assert "accents" in data["options"]
    assert "line_spacings" in data["options"]
    assert "line_spacing_default" in data["options"]
    assert "word_spacings" in data["options"]
    assert "word_spacing_default" in data["options"]


def test_get_style_returns_defaults_when_no_override(api_client, user, resume):
    api_client.force_authenticate(user=user)
    response = api_client.get(f"/api/resumes/{resume.id}/style/")
    data = response.json()
    assert data["style"]["font"] == "lmodern"
    assert data["style"]["accent"] == "#4B41C8"
    assert data["style"]["line_spacing"] == "1.00"
    assert data["style"]["word_spacing"] == "1.00"


def test_get_style_404_for_other_user(api_client, other_user, resume):
    api_client.force_authenticate(user=other_user)
    response = api_client.get(f"/api/resumes/{resume.id}/style/")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /api/resumes/<id>/style/
# ---------------------------------------------------------------------------

def test_patch_style_font_change(api_client, user, resume, monkeypatch):
    api_client.force_authenticate(user=user)
    monkeypatch.setattr(
        "resumes.views.compile_latex",
        lambda _: b"%PDF-1.4 stub",
    )
    monkeypatch.setattr(
        "resumes.views.assemble_resume_latex",
        lambda _resume: "\\documentclass{article}\\begin{document}hi\\end{document}",
    )

    response = api_client.patch(
        f"/api/resumes/{resume.id}/style/",
        data={"font": "times"},
        format="json",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["changed"] is True
    assert data["style"]["font"] == "times"
    assert "pdf" in data
    assert "latex" in data

    resume.refresh_from_db()
    assert resume.config_override["style"]["font"] == "times"


def test_patch_style_spacing_change(api_client, user, resume, monkeypatch):
    import fitz
    doc = fitz.open()
    doc.new_page()
    valid_pdf = doc.tobytes()

    api_client.force_authenticate(user=user)
    monkeypatch.setattr(
        "resumes.views.compile_latex",
        lambda _: valid_pdf,
    )
    monkeypatch.setattr(
        "resumes.views.assemble_resume_latex",
        lambda _resume: "\\documentclass{article}\\begin{document}hi\\end{document}",
    )

    response = api_client.patch(
        f"/api/resumes/{resume.id}/style/",
        data={"line_spacing": "1.10", "word_spacing": "1.15"},
        format="json",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["changed"] is True
    assert data["style"]["line_spacing"] == "1.10"
    assert data["style"]["word_spacing"] == "1.15"
    assert "pdf" in data
    assert "latex" in data
    assert "pages" in data
    assert "page_count" in data

    resume.refresh_from_db()
    assert resume.config_override["style"]["line_spacing"] == "1.10"
    assert resume.config_override["style"]["word_spacing"] == "1.15"


def test_patch_style_400_invalid_spacing(api_client, user, resume):
    api_client.force_authenticate(user=user)
    response = api_client.patch(
        f"/api/resumes/{resume.id}/style/",
        data={"line_spacing": "1.07"},
        format="json",
    )
    assert response.status_code == 400


def test_patch_style_no_change(api_client, user, resume):
    """Patching with the already-resolved default style returns changed=False and does not compile."""
    api_client.force_authenticate(user=user)
    response = api_client.patch(
        f"/api/resumes/{resume.id}/style/",
        data={"font": "lmodern", "accent": "#4B41C8"},
        format="json",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["changed"] is False
    assert "pdf" not in data


def test_patch_style_400_unknown_font(api_client, user, resume):
    api_client.force_authenticate(user=user)
    response = api_client.patch(
        f"/api/resumes/{resume.id}/style/",
        data={"font": "wingdings"},
        format="json",
    )
    assert response.status_code == 400


def test_patch_style_400_bad_hex(api_client, user, resume):
    api_client.force_authenticate(user=user)
    response = api_client.patch(
        f"/api/resumes/{resume.id}/style/",
        data={"accent": "#ZZZZZZ"},
        format="json",
    )
    assert response.status_code == 400


def test_patch_style_400_low_contrast(api_client, user, resume):
    api_client.force_authenticate(user=user)
    response = api_client.patch(
        f"/api/resumes/{resume.id}/style/",
        data={"accent": "#FFFF00"},
        format="json",
    )
    assert response.status_code == 400
    assert "contrast" in str(response.json()).lower()


def test_patch_style_400_empty_body(api_client, user, resume):
    api_client.force_authenticate(user=user)
    response = api_client.patch(
        f"/api/resumes/{resume.id}/style/",
        data={},
        format="json",
    )
    assert response.status_code == 400


def test_patch_style_400_unknown_keys(api_client, user, resume):
    api_client.force_authenticate(user=user)
    response = api_client.patch(
        f"/api/resumes/{resume.id}/style/",
        data={"colour": "#4B41C8"},
        format="json",
    )
    assert response.status_code == 400


def test_patch_style_404_other_user(api_client, other_user, resume):
    api_client.force_authenticate(user=other_user)
    response = api_client.patch(
        f"/api/resumes/{resume.id}/style/",
        data={"font": "times"},
        format="json",
    )
    assert response.status_code == 404


def test_patch_style_rollback_on_compile_failure(api_client, user, resume, monkeypatch):
    """If compile fails, the style must be rolled back to its pre-patch value."""
    api_client.force_authenticate(user=user)

    resume.config_override = {"style": {"font": "lmodern", "accent": "#4B41C8"}}
    resume.save(update_fields=["config_override"])

    monkeypatch.setattr(
        "resumes.views.assemble_resume_latex",
        lambda _: "some latex",
    )

    def failing_compile(_):
        raise RuntimeError("pdflatex compilation error")

    monkeypatch.setattr(
        "resumes.views.compile_latex",
        failing_compile,
    )

    response = api_client.patch(
        f"/api/resumes/{resume.id}/style/",
        data={"font": "times"},
        format="json",
    )
    assert response.status_code == 422

    # Style must be rolled back to pre-patch state
    resume.refresh_from_db()
    assert resume.config_override["style"]["font"] == "lmodern"
