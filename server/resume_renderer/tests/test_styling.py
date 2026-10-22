"""
Tests for resume_renderer.services.styling and render styling pipeline.
"""
import pytest
from unittest.mock import MagicMock
from rest_framework import serializers as drf_serializers

from decimal import Decimal
from resume_renderer.services.styling import (
    DEFAULT_ACCENT,
    DEFAULT_FONT,
    DEFAULT_LINE_SPACING,
    DEFAULT_WORD_SPACING,
    DEFAULT_SPACING_OPTIONS,
    FONTS,
    FONT_LABELS,
    _contrast_ratio_vs_white,
    _validate_hex,
    apply_style,
    build_spacing_setup,
    get_style_options,
    parse_spacing,
    resolve_style,
    validate_style_patch,
    validate_template_style_config,
)
from resume_renderer.services.renderer import (
    assemble_resume_latex,
    compile_latex,
    fill_placeholders,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_template(config=None):
    t = MagicMock()
    t.template_config = config or {}
    return t


def _make_resume(config_override=None, template_config=None):
    r = MagicMock()
    r.config_override = config_override if config_override is not None else {}
    r.template = _make_template(template_config)
    r.latex_cache_valid = True
    return r


# ---------------------------------------------------------------------------
# _validate_hex
# ---------------------------------------------------------------------------

def test_validate_hex_valid():
    assert _validate_hex("#4b41c8") == "#4B41C8"
    assert _validate_hex("#FFFFFF") == "#FFFFFF"
    assert _validate_hex("#000000") == "#000000"


def test_validate_hex_rejects_short():
    with pytest.raises(drf_serializers.ValidationError):
        _validate_hex("#123")


def test_validate_hex_rejects_invalid_char():
    with pytest.raises(drf_serializers.ValidationError):
        _validate_hex("#12345G")


def test_validate_hex_rejects_non_string():
    with pytest.raises(drf_serializers.ValidationError):
        _validate_hex(123456)


# ---------------------------------------------------------------------------
# WCAG contrast
# ---------------------------------------------------------------------------

def test_default_accent_passes_contrast():
    """Default accent #4B41C8 must have contrast >= 3:1 against white."""
    ratio = _contrast_ratio_vs_white(DEFAULT_ACCENT)
    assert ratio >= 3.0, f"Default accent contrast {ratio:.2f}:1 is below 3:1"


def test_yellow_fails_contrast():
    """#FFFF00 has contrast ~1.07:1 against white and must be rejected."""
    ratio = _contrast_ratio_vs_white("#FFFF00")
    assert ratio < 3.0


def test_white_fails_contrast():
    ratio = _contrast_ratio_vs_white("#FFFFFF")
    assert ratio < 3.0


# ---------------------------------------------------------------------------
# parse_spacing and build_spacing_setup
# ---------------------------------------------------------------------------

def test_parse_spacing_valid():
    assert parse_spacing("1.00") == Decimal("1.00")
    assert parse_spacing("1.10") == Decimal("1.10")
    assert parse_spacing("0.90") == Decimal("0.90")
    assert parse_spacing(1.15) == Decimal("1.15")
    assert parse_spacing(1) == Decimal("1.00")
    assert parse_spacing(Decimal("1.05")) == Decimal("1.05")


def test_parse_spacing_rejects_invalid():
    for val in [True, False, None, "abc", "NaN", "inf", "-1.00", -0.5, ""]:
        with pytest.raises(drf_serializers.ValidationError):
            parse_spacing(val)


def test_build_spacing_setup_default_empty():
    assert build_spacing_setup("1.00", "1.00") == ""


def test_build_spacing_setup_line_only():
    out = build_spacing_setup("1.10", "1.00")
    assert r"\linespread{1.10}" in out
    assert r"\renewenvironment{localsize}" in out
    assert r"etoolbox" not in out
    assert r"\spaceskip" not in out
    assert out.endswith("\n")


def test_build_spacing_setup_word_only():
    out = build_spacing_setup("1.00", "1.15")
    assert r"\usepackage{etoolbox}" in out
    assert r"\spaceskip=1.15\fontdimen2\font plus 1.15\fontdimen3\font minus 1.15\fontdimen4\font\relax" in out
    assert r"\linespread" not in out
    assert r"localsize" not in out
    assert out.endswith("\n")


def test_build_spacing_setup_both():
    out = build_spacing_setup("1.10", "1.15")
    assert r"\linespread{1.10}" in out
    assert r"\renewenvironment{localsize}" in out
    assert r"\usepackage{etoolbox}" in out
    assert r"\spaceskip=1.15\fontdimen2\font" in out
    assert out.endswith("\n")


# ---------------------------------------------------------------------------
# get_style_options
# ---------------------------------------------------------------------------

def test_get_style_options_defaults():
    t = _make_template()
    opts = get_style_options(t)
    assert "fonts" in opts
    assert "accents" in opts
    assert all(f["key"] in FONTS for f in opts["fonts"])
    assert opts["font_default"] == DEFAULT_FONT
    assert opts["accent_default"] == DEFAULT_ACCENT
    assert opts["line_spacings"] == DEFAULT_SPACING_OPTIONS
    assert opts["line_spacing_default"] == DEFAULT_LINE_SPACING
    assert opts["word_spacings"] == DEFAULT_SPACING_OPTIONS
    assert opts["word_spacing_default"] == DEFAULT_WORD_SPACING


def test_get_style_options_custom():
    t = _make_template({
        "font_options": ["lmodern", "times"],
        "font_default": "times",
        "accent_options": ["#4B41C8", "#1A6B3C"],
        "accent_default": "#1A6B3C",
    })
    opts = get_style_options(t)
    assert [f["key"] for f in opts["fonts"]] == ["lmodern", "times"]
    assert opts["font_default"] == "times"
    assert opts["accent_default"] == "#1A6B3C"


def test_get_style_options_strips_unknown_font_keys():
    t = _make_template({"font_options": ["lmodern", "comic-sans", "times"]})
    opts = get_style_options(t)
    keys = [f["key"] for f in opts["fonts"]]
    assert "comic-sans" not in keys
    assert "lmodern" in keys
    assert "times" in keys


# ---------------------------------------------------------------------------
# resolve_style
# ---------------------------------------------------------------------------

def test_resolve_style_returns_defaults_when_no_override():
    r = _make_resume()
    s = resolve_style(r)
    assert s["font"] == DEFAULT_FONT
    assert s["accent"] == DEFAULT_ACCENT.upper()


def test_resolve_style_uses_stored_values():
    r = _make_resume(config_override={"style": {"font": "times", "accent": "#1A6B3C"}})
    s = resolve_style(r)
    assert s["font"] == "times"
    assert s["accent"] == "#1A6B3C"


def test_resolve_style_ignores_unknown_font():
    r = _make_resume(config_override={"style": {"font": "wingdings"}})
    s = resolve_style(r)
    assert s["font"] == DEFAULT_FONT


def test_resolve_style_ignores_bad_hex():
    r = _make_resume(config_override={"style": {"accent": "not-a-colour"}})
    s = resolve_style(r)
    assert s["accent"] == DEFAULT_ACCENT.upper()


def test_resolve_style_normalises_accent_to_uppercase():
    r = _make_resume(config_override={"style": {"accent": "#4b41c8"}})
    s = resolve_style(r)
    assert s["accent"] == "#4B41C8"


def test_resolve_style_uses_stored_spacing():
    r = _make_resume(config_override={"style": {"line_spacing": "1.10", "word_spacing": "1.15"}})
    s = resolve_style(r)
    assert s["line_spacing"] == "1.10"
    assert s["word_spacing"] == "1.15"


def test_resolve_style_ignores_invalid_spacing():
    r = _make_resume(config_override={"style": {"line_spacing": "9.99", "word_spacing": "not-a-number"}})
    s = resolve_style(r)
    assert s["line_spacing"] == DEFAULT_LINE_SPACING
    assert s["word_spacing"] == DEFAULT_WORD_SPACING


# ---------------------------------------------------------------------------
# validate_style_patch
# ---------------------------------------------------------------------------

def test_validate_patch_accepts_valid_font():
    t = _make_template()
    result = validate_style_patch({"font": "times"}, t)
    assert result == {"font": "times"}


def test_validate_patch_accepts_valid_accent():
    t = _make_template()
    result = validate_style_patch({"accent": "#1A4B8C"}, t)
    assert result["accent"] == "#1A4B8C"


def test_validate_patch_accepts_spacing():
    t = _make_template()
    result = validate_style_patch({"line_spacing": "1.10", "word_spacing": "1.15"}, t)
    assert result["line_spacing"] == "1.10"
    assert result["word_spacing"] == "1.15"


def test_validate_patch_rejects_spacing_not_in_options():
    t = _make_template()
    with pytest.raises(drf_serializers.ValidationError):
        validate_style_patch({"line_spacing": "1.07"}, t)

    with pytest.raises(drf_serializers.ValidationError):
        validate_style_patch({"word_spacing": "2.00"}, t)


def test_validate_patch_rejects_non_numeric_spacing():
    t = _make_template()
    with pytest.raises(drf_serializers.ValidationError):
        validate_style_patch({"line_spacing": "abc"}, t)


def test_validate_patch_accepts_all_style_fields():
    t = _make_template()
    result = validate_style_patch({
        "font": "charter",
        "accent": "#1A4B8C",
        "line_spacing": "0.95",
        "word_spacing": "1.05",
    }, t)
    assert result == {
        "font": "charter",
        "accent": "#1A4B8C",
        "line_spacing": "0.95",
        "word_spacing": "1.05",
    }


def test_validate_patch_rejects_empty_body():
    t = _make_template()
    with pytest.raises(drf_serializers.ValidationError):
        validate_style_patch({}, t)


def test_validate_patch_rejects_unknown_keys():
    t = _make_template()
    with pytest.raises(drf_serializers.ValidationError):
        validate_style_patch({"color": "#aabbcc"}, t)


def test_validate_patch_rejects_unknown_font():
    t = _make_template()
    with pytest.raises(drf_serializers.ValidationError):
        validate_style_patch({"font": "comic-sans"}, t)


def test_validate_patch_rejects_bad_hex():
    t = _make_template()
    with pytest.raises(drf_serializers.ValidationError):
        validate_style_patch({"accent": "#12345G"}, t)


def test_validate_patch_rejects_short_hex():
    t = _make_template()
    with pytest.raises(drf_serializers.ValidationError):
        validate_style_patch({"accent": "#123"}, t)


def test_validate_patch_rejects_low_contrast_yellow():
    t = _make_template()
    with pytest.raises(drf_serializers.ValidationError) as exc_info:
        validate_style_patch({"accent": "#FFFF00"}, t)
    assert "contrast" in str(exc_info.value).lower()


def test_validate_patch_rejects_injection_in_font():
    t = _make_template()
    with pytest.raises(drf_serializers.ValidationError):
        validate_style_patch({"font": r"palatino}\input{/etc/passwd}"}, t)


def test_validate_patch_rejects_injection_in_accent():
    t = _make_template()
    with pytest.raises(drf_serializers.ValidationError):
        validate_style_patch({"accent": r"#4B41C8}\input{/etc/passwd}"}, t)


# ---------------------------------------------------------------------------
# fill_placeholders
# ---------------------------------------------------------------------------

def test_fill_placeholders_single_pass_no_double_substitution():
    """Ensure user content containing placeholder tokens is NOT re-substituted."""
    preamble = "__FONT_SETUP__\n__ACCENT_HEX__\n__CONTENT__"
    values = {
        "__FONT_SETUP__": r"\usepackage{lmodern}",
        "__ACCENT_HEX__": "4B41C8",
        "__CONTENT__": "User text with literal __FONT_SETUP__ inside",
    }
    result = fill_placeholders(preamble, values)
    assert result == "\\usepackage{lmodern}\n4B41C8\nUser text with literal __FONT_SETUP__ inside"


# ---------------------------------------------------------------------------
# apply_style (Django DB)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_apply_style_no_change_returns_false():
    from django.contrib.auth import get_user_model
    from resumes.models import Resume, ResumeTemplate, VisualTheme

    user = get_user_model().objects.create_user(username="styler_test", password="pass")
    theme = VisualTheme.objects.create(
        key="test-theme-apply",
        display_name="Test",
        compatible_families=["iitb"],
        converter_set_key="iitb-classic",
        latex_preamble="__FONT_SETUP__\n__ACCENT_HEX__\n__CONTENT__",
    )
    template = ResumeTemplate.objects.create(
        key="test-tmpl-apply",
        display_name="Test",
        family="iitb",
        domain="general",
        template_config={},
    )
    template.available_themes.add(theme)
    resume = Resume.objects.create(
        owner=user,
        title="Test",
        template=template,
        visual_theme=theme,
        config_override={"style": {"font": "lmodern", "accent": "#4B41C8"}},
    )

    result = apply_style(resume, {"font": "lmodern", "accent": "#4B41C8"})
    assert result is False
    resume.refresh_from_db()
    assert resume.latex_cache_valid is False


@pytest.mark.django_db
def test_apply_style_change_returns_true_and_invalidates_cache():
    from django.contrib.auth import get_user_model
    from resumes.models import Resume, ResumeTemplate, VisualTheme

    user = get_user_model().objects.create_user(username="styler_test2", password="pass")
    theme = VisualTheme.objects.create(
        key="test-theme-apply2",
        display_name="Test",
        compatible_families=["iitb"],
        converter_set_key="iitb-classic",
        latex_preamble="__FONT_SETUP__\n__ACCENT_HEX__\n__CONTENT__",
    )
    template = ResumeTemplate.objects.create(
        key="test-tmpl-apply2",
        display_name="Test",
        family="iitb",
        domain="general",
        template_config={},
    )
    template.available_themes.add(theme)
    resume = Resume.objects.create(
        owner=user,
        title="Test",
        template=template,
        visual_theme=theme,
        config_override={"other_key": "preserved"},
        latex_cache_valid=True,
    )

    result = apply_style(resume, {"font": "times"})
    assert result is True
    resume.refresh_from_db()
    assert resume.latex_cache_valid is False
    assert resume.config_override["style"]["font"] == "times"
    assert resume.config_override.get("other_key") == "preserved"


@pytest.mark.django_db
def test_apply_style_spacing_change():
    from django.contrib.auth import get_user_model
    from resumes.models import Resume, ResumeTemplate, VisualTheme

    user = get_user_model().objects.create_user(username="styler_test3", password="pass")
    theme = VisualTheme.objects.create(
        key="test-theme-apply3",
        display_name="Test",
        compatible_families=["iitb"],
        converter_set_key="iitb-classic",
        latex_preamble="__FONT_SETUP__\n__ACCENT_HEX__\n__CONTENT__",
    )
    template = ResumeTemplate.objects.create(
        key="test-tmpl-apply3",
        display_name="Test",
        family="iitb",
        domain="general",
        template_config={},
    )
    template.available_themes.add(theme)
    resume = Resume.objects.create(
        owner=user,
        title="Test Spacing",
        template=template,
        visual_theme=theme,
        config_override={},
        latex_cache_valid=True,
    )

    result = apply_style(resume, {"line_spacing": "1.10", "word_spacing": "1.15"})
    assert result is True
    resume.refresh_from_db()
    assert resume.latex_cache_valid is False
    assert resume.config_override["style"]["line_spacing"] == "1.10"
    assert resume.config_override["style"]["word_spacing"] == "1.15"

    # Same patch returns False
    result2 = apply_style(resume, {"line_spacing": "1.10", "word_spacing": "1.15"})
    assert result2 is False


# ---------------------------------------------------------------------------
# Golden test (assemble_resume_latex with default style)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_assemble_resume_latex_default_matches_golden_structure():
    """Verify default assemble_resume_latex fills lmodern and 4B41C8 with no leftover placeholders."""
    from django.contrib.auth import get_user_model
    from resumes.models import Resume, ResumeTemplate, VisualTheme

    user = get_user_model().objects.create_user(username="golden_user", password="pass")
    theme = VisualTheme.objects.create(
        key="golden-theme",
        display_name="Golden Theme",
        compatible_families=["iitb"],
        converter_set_key="iitb-classic",
        latex_preamble=(
            "\\documentclass{article}\n"
            "__FONT_SETUP__\n"
            "\\definecolor{myblue}{HTML}{__ACCENT_HEX__}\n"
            "__SPACING_SETUP__\\begin{document}\n"
            "__CONTENT__\n"
            "\\end{document}\n"
        ),
    )
    template = ResumeTemplate.objects.create(
        key="golden-template",
        display_name="Golden Template",
        family="iitb",
        domain="general",
        template_config={},
    )
    template.available_themes.add(theme)
    resume = Resume.objects.create(
        owner=user,
        title="Golden Resume",
        template=template,
        visual_theme=theme,
        config_override={},
    )

    latex = assemble_resume_latex(resume)

    expected = (
        "\\documentclass{article}\n"
        "\\usepackage{lmodern}\n"
        "\\definecolor{myblue}{HTML}{4B41C8}\n"
        "\\begin{document}\n"
        "\n"
        "\\end{document}\n"
    )
    assert latex == expected
    assert "__FONT_SETUP__" not in latex
    assert "__ACCENT_HEX__" not in latex
    assert "__CONTENT__" not in latex


@pytest.mark.django_db
def test_assemble_resume_latex_raises_on_unfilled_placeholder():
    """If preamble contains an unrecognised placeholder, RuntimeError is raised."""
    from django.contrib.auth import get_user_model
    from resumes.models import Resume, ResumeTemplate, VisualTheme

    user = get_user_model().objects.create_user(username="error_user", password="pass")
    theme = VisualTheme.objects.create(
        key="err-theme",
        display_name="Err Theme",
        compatible_families=["iitb"],
        converter_set_key="iitb-classic",
        latex_preamble=(
            "__FONT_SETUP__\n__ACCENT_HEX__\n__SPACING_SETUP__\n__CONTENT__\n__UNKNOWN_TAG__"
        ),
    )
    template = ResumeTemplate.objects.create(
        key="err-template",
        display_name="Err Template",
        family="iitb",
        domain="general",
        template_config={},
    )
    template.available_themes.add(theme)
    resume = Resume.objects.create(
        owner=user,
        title="Err Resume",
        template=template,
        visual_theme=theme,
    )

    with pytest.raises(RuntimeError) as exc_info:
        assemble_resume_latex(resume)
    assert "__UNKNOWN_TAG__" in str(exc_info.value)


# ---------------------------------------------------------------------------
# compile_latex cache and isolation tests
# ---------------------------------------------------------------------------

def test_compile_cache_prevents_duplicate_docker_calls(monkeypatch):
    """Same LaTeX string should hit the cache on the second call, avoiding Docker."""
    from django.core.cache import cache

    cache.clear()
    call_count = {"n": 0}

    class FakeContainer:
        def exec_run(self, cmd, workdir=None):
            call_count["n"] += 1
            return 0, b"ok"

        def put_archive(self, path, data):
            pass

        def get_archive(self, path):
            import tarfile, io
            buf = io.BytesIO()
            with tarfile.open(fileobj=buf, mode="w") as t:
                pdf_data = b"%PDF-1.4 stub"
                info = tarfile.TarInfo(name="main.pdf")
                info.size = len(pdf_data)
                t.addfile(info, io.BytesIO(pdf_data))
            buf.seek(0)
            return iter([buf.read()]), None

    monkeypatch.setattr(
        "resume_renderer.services.renderer._get_latex_container",
        lambda: FakeContainer(),
    )
    monkeypatch.setattr(
        "resume_renderer.services.renderer._get_docker_client",
        lambda: True,
    )

    latex = "\\documentclass{article}\\begin{document}hello\\end{document}"
    pdf1 = compile_latex(latex)
    pdf2 = compile_latex(latex)

    assert pdf1 == pdf2
    # exec_run was called during the first compile; second compile was cache hit
    initial_calls = call_count["n"]
    assert initial_calls > 0
    # Third compile with same latex
    pdf3 = compile_latex(latex)
    assert call_count["n"] == initial_calls


def test_compile_latex_uses_unique_workdirs(monkeypatch):
    """Two different compile calls must use distinct per-job working directories."""
    from django.core.cache import cache

    cache.clear()
    seen_workdirs = []

    class FakeContainer:
        def exec_run(self, cmd, workdir=None):
            if workdir:
                seen_workdirs.append(workdir)
            return 0, b"ok"

        def put_archive(self, path, data):
            pass

        def get_archive(self, path):
            import tarfile, io
            buf = io.BytesIO()
            with tarfile.open(fileobj=buf, mode="w") as t:
                pdf_data = b"%PDF-1.4 stub"
                info = tarfile.TarInfo(name="main.pdf")
                info.size = len(pdf_data)
                t.addfile(info, io.BytesIO(pdf_data))
            buf.seek(0)
            return iter([buf.read()]), None

    monkeypatch.setattr(
        "resume_renderer.services.renderer._get_latex_container",
        lambda: FakeContainer(),
    )
    monkeypatch.setattr(
        "resume_renderer.services.renderer._get_docker_client",
        lambda: True,
    )

    compile_latex("job 1 unique string")
    compile_latex("job 2 unique string")

    # Filter distinct workdirs
    unique_dirs = set(seen_workdirs)
    assert len(unique_dirs) >= 2


# ---------------------------------------------------------------------------
# Docker tests (run only when Docker container is running)
# ---------------------------------------------------------------------------

@pytest.mark.docker
def test_all_fonts_and_accent_compile_in_docker():
    """Verify each font key and an accent compile successfully in Docker."""
    from resume_renderer.services.renderer import _get_docker_client

    if _get_docker_client() is None:
        pytest.skip("Docker is not available")

    test_accent = "1A6B3C"
    sample_doc = r"""
\documentclass{article}
__FONT_SETUP__
\usepackage[table, svgnames]{xcolor}
\definecolor{myblue}{HTML}{__ACCENT_HEX__}
\begin{document}
{\color{myblue} Testing font and color compilation.}
\end{document}
"""
    for font_key in FONTS:
        values = {
            "__FONT_SETUP__": FONTS[font_key],
            "__ACCENT_HEX__": test_accent,
        }
        filled = fill_placeholders(sample_doc, values)
        assert "__FONT_SETUP__" not in filled
        assert "__ACCENT_HEX__" not in filled
        try:
            pdf_bytes = compile_latex(filled)
            assert pdf_bytes.startswith(b"%PDF")
        except Exception as exc:
            pytest.fail(f"Compilation failed for font '{font_key}': {exc}")
