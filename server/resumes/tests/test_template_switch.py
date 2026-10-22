"""
Tests for template font sets, template list endpoint, and template switch endpoint.
"""
import copy
import json
import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework.test import APIClient

from resumes.models import Resume, ResumeTemplate, Section, SectionEntry, VisualTheme
from resumes.services.template_switch import plan_switch, apply_switch
from resume_renderer.services.styling import (
    DEFAULT_FONT,
    FONTS,
    FONT_LABELS,
    validate_template_style_config,
    validate_style_patch,
    resolve_style,
)
from resume_renderer.services.renderer import assemble_resume_latex


def _docker_available():
    try:
        import docker
        c = docker.from_env()
        c.ping()
        return True
    except Exception:
        return False


requires_docker = pytest.mark.skipif(not _docker_available(), reason="Docker is not available")


@pytest.fixture()
def api_client():
    return APIClient()


@pytest.fixture()
def user(db):
    return get_user_model().objects.create_user(username="testuser_switch", password="password123")


@pytest.fixture()
def other_user(db):
    return get_user_model().objects.create_user(username="otheruser_switch", password="password123")


@pytest.fixture(autouse=True)
def seeded_db(db):
    call_command("seed_templates")


@pytest.fixture()
def mock_latex(monkeypatch):
    """Default mock for LaTeX compilation in unit tests."""
    monkeypatch.setattr(
        "resumes.services.template_switch.assemble_resume_latex",
        lambda r: "% renderer-v2\n\\dummy{latex}",
    )
    monkeypatch.setattr(
        "resumes.services.template_switch.compile_latex",
        lambda ltx: b"%PDF-1.4 dummy pdf bytes",
    )


@pytest.fixture()
def sample_resume(user):
    template = ResumeTemplate.objects.get(key="iitb-general")
    theme = template.available_themes.first()

    resume = Resume.objects.create(
        owner=user,
        title="Sample Resume",
        template=template,
        visual_theme=theme,
        pages=1,
        config_override={"custom_metadata": "keep_this_safe"},
    )

    # Populate sections from template manifest
    for tst in template.section_manifest.select_related("section_type").order_by("default_order"):
        sec = Section.objects.create(
            resume=resume,
            section_type=tst.section_type,
            order=tst.default_order,
            is_visible=True,
        )
        # Add content to scholastic_achievements and experience
        if tst.section_type.key == "scholastic_achievements":
            SectionEntry.objects.create(
                section=sec,
                order=0,
                raw_input="Rank 1",
                content={"text": "Top Rank in Department", "year": "2024"},
                generation_status="done",
            )
        elif tst.section_type.key == "professional_experience":
            SectionEntry.objects.create(
                section=sec,
                order=0,
                raw_input="SWE intern",
                content={
                    "title": "Software Engineer",
                    "organization": "Acme Corp",
                    "location": "Mumbai",
                    "timeline": "Summer 2025",
                    "summary": "Full stack work",
                    "bullets": ["Built stuff"],
                },
                generation_status="done",
            )
        elif not tst.section_type.allow_multiple_entries:
            SectionEntry.objects.create(
                section=sec,
                order=0,
                raw_input="",
                content={"name": "Alice Developer"},
                generation_status="done",
            )

    return resume


# ---------------------------------------------------------------------------
# Phase 1 A: Font Sets & Seed Validation
# ---------------------------------------------------------------------------

def test_seed_validation_rules_and_font_sets():
    """Verify each seeded template has 2-3 fonts and defaults match constraints."""
    expected_fonts = {
        "iitb-general": ("lmodern", ["lmodern", "times", "palatino"]),
        "external-standard": ("lmodern", ["lmodern", "times", "palatino"]),
        "awesome-cv-general": ("sourcesans", ["sourcesans", "helvetica", "lmodern"]),
        "jake-general": ("lmodern", ["lmodern", "times", "palatino"]),
    }

    for key, (def_font, opt_fonts) in expected_fonts.items():
        tmpl = ResumeTemplate.objects.get(key=key)
        cfg = tmpl.template_config
        assert cfg["font_default"] == def_font
        assert cfg["font_options"] == opt_fonts
        assert 2 <= len(cfg["font_options"]) <= 3
        assert cfg["font_default"] in cfg["font_options"]
        assert all(f in FONTS for f in cfg["font_options"])
        assert cfg["accent_default"] in cfg["accent_options"]
        # Must pass helper
        validate_template_style_config(cfg)


def test_seed_validation_helper_rejects_invalid_configs():
    with pytest.raises(ValueError, match="between 2 and 3 fonts"):
        validate_template_style_config({
            "font_default": "lmodern",
            "font_options": ["lmodern"],  # < 2
            "accent_default": "#4B41C8",
            "accent_options": ["#4B41C8"],
        })

    with pytest.raises(ValueError, match="between 2 and 3 fonts"):
        validate_template_style_config({
            "font_default": "lmodern",
            "font_options": ["lmodern", "times", "palatino", "charter"],  # > 3
            "accent_default": "#4B41C8",
            "accent_options": ["#4B41C8"],
        })

    with pytest.raises(ValueError, match="Unknown font 'wingdings'"):
        validate_template_style_config({
            "font_default": "lmodern",
            "font_options": ["lmodern", "wingdings"],
            "accent_default": "#4B41C8",
            "accent_options": ["#4B41C8"],
        })

    with pytest.raises(ValueError, match="font_default 'times' must be present"):
        validate_template_style_config({
            "font_default": "times",
            "font_options": ["lmodern", "palatino"],
            "accent_default": "#4B41C8",
            "accent_options": ["#4B41C8"],
        })

    with pytest.raises(ValueError, match="accent_default '#000000' must be present"):
        validate_template_style_config({
            "font_default": "lmodern",
            "font_options": ["lmodern", "times"],
            "accent_default": "#000000",
            "accent_options": ["#4B41C8"],
        })


def test_validate_style_patch_against_current_template_options():
    """validate_style_patch must reject a font in global FONTS if not in current template options."""
    jake_tmpl = ResumeTemplate.objects.get(key="jake-general")
    # "helvetica" is in FONTS, but NOT in jake-general's font_options
    with pytest.raises(Exception) as exc_info:
        validate_style_patch({"font": "helvetica"}, jake_tmpl)
    assert "helvetica" in str(exc_info.value)

    # "palatino" IS in jake-general's font_options
    cleaned = validate_style_patch({"font": "palatino"}, jake_tmpl)
    assert cleaned["font"] == "palatino"


def test_resolve_style_falls_back_when_stored_font_not_offered(sample_resume):
    # Resume stores "charter", which is not offered in iitb-general
    sample_resume.config_override = {"style": {"font": "charter", "accent": "#4B41C8"}}
    st = resolve_style(sample_resume)
    assert st["font"] == "lmodern"  # falls back to template default


def test_lowercase_custom_accent_hex(sample_resume, monkeypatch):
    """Check that lowercase accent is normalized to uppercase 6 hex digits."""
    sample_resume.config_override = {"style": {"accent": "#1a6b3c"}}
    latex = assemble_resume_latex(sample_resume)
    assert "1A6B3C" in latex
    assert "#1a6b3c" not in latex


# ---------------------------------------------------------------------------
# Phase 1 B: Template List API
# ---------------------------------------------------------------------------

def test_template_list_endpoint(api_client, user):
    api_client.force_authenticate(user=user)

    for url in ["/api/resumes/templates/", "/api/templates/"]:
        res = api_client.get(url)
        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 4

        for item in data:
            assert "key" in item
            assert "display_name" in item
            assert "family" in item
            assert "default_theme_key" in item
            assert "fonts" in item
            assert len(item["fonts"]) in (2, 3)
            for f in item["fonts"]:
                assert "key" in f and "label" in f
            assert "font_default" in item
            assert "accents" in item
            assert isinstance(item["accents"], list)
            assert "accent_default" in item
            assert "line_spacings" in item
            assert isinstance(item["line_spacings"], list)
            assert "line_spacing_default" in item
            assert "word_spacings" in item
            assert isinstance(item["word_spacings"], list)
            assert "word_spacing_default" in item
            assert "sections" in item
            for s in item["sections"]:
                assert "key" in s
                assert "display_name" in s
                assert "is_default" in s
                assert "is_required" in s
                assert "default_order" in s


def test_resume_detail_includes_template_key(api_client, user, sample_resume):
    api_client.force_authenticate(user=user)
    res = api_client.get(f"/api/resumes/{sample_resume.id}/")
    assert res.status_code == 200
    data = res.json()
    assert data["template"]["key"] == "iitb-general"
    assert data["template"]["font_default"] == "lmodern"
    assert data["template"]["accent_default"] == "#4B41C8"
    assert data["template_key"] == "iitb-general"


# ---------------------------------------------------------------------------
# Phase 1 C & D: Template Switch Endpoint
# ---------------------------------------------------------------------------

def test_switch_endpoint_validation_errors(api_client, user, other_user, sample_resume, mock_latex):
    # Unauthenticated
    res = api_client.post(f"/api/resumes/{sample_resume.id}/template/", {"template_key": "external-standard"}, format="json")
    assert res.status_code in (401, 403)

    api_client.force_authenticate(user=user)

    # Inactive / unknown template
    res = api_client.post(f"/api/resumes/{sample_resume.id}/template/", {"template_key": "nonexistent"}, format="json")
    assert res.status_code == 400

    # Incompatible theme
    res = api_client.post(
        f"/api/resumes/{sample_resume.id}/template/",
        {"template_key": "iitb-general", "theme_key": "jake-classic"},
        format="json",
    )
    assert res.status_code == 400

    # Other user forbidden / 404
    api_client.force_authenticate(user=other_user)
    res = api_client.post(f"/api/resumes/{sample_resume.id}/template/", {"template_key": "external-standard"}, format="json")
    assert res.status_code == 404


def test_switch_idempotency_same_template(api_client, user, sample_resume, mock_latex):
    api_client.force_authenticate(user=user)
    res = api_client.post(
        f"/api/resumes/{sample_resume.id}/template/",
        {"template_key": "iitb-general", "theme_key": "iitb-classic"},
        format="json",
    )
    assert res.status_code == 200
    data = res.json()
    assert data["changed"] is False
    assert data["template"]["key"] == "iitb-general"


def test_switch_dry_run_writes_nothing(api_client, user, sample_resume, monkeypatch):
    api_client.force_authenticate(user=user)

    def failing_compile(_):
        raise RuntimeError("compile_latex should not be called on dry_run")

    monkeypatch.setattr("resumes.services.template_switch.compile_latex", failing_compile)

    orig_sections = list(sample_resume.sections.values("id", "order", "is_visible"))
    orig_template_id = sample_resume.template_id

    res = api_client.post(
        f"/api/resumes/{sample_resume.id}/template/",
        {"template_key": "external-standard", "dry_run": True},
        format="json",
    )
    assert res.status_code == 200
    data = res.json()
    assert data["dry_run"] is True
    assert "plan" in data
    assert "will_hide" in data["plan"]
    assert "will_add_empty" in data["plan"]
    assert "will_restore" in data["plan"]
    assert "style_reset" in data["plan"]
    assert "unchanged" in data["plan"]

    # Assert no DB changes
    sample_resume.refresh_from_db()
    assert sample_resume.template_id == orig_template_id
    curr_sections = list(sample_resume.sections.values("id", "order", "is_visible"))
    assert curr_sections == orig_sections


def test_round_trip_a_b_a_preserves_sections_order_visibility_and_entries(api_client, user, sample_resume, mock_latex):
    api_client.force_authenticate(user=user)

    initial_sections_snapshot = [
        (s.section_type.key, s.order, s.is_visible, s.entries.count())
        for s in sample_resume.sections.order_by("order")
    ]
    initial_entries_count = SectionEntry.objects.filter(section__resume=sample_resume).count()

    # Switch A -> B (iitb-general -> external-standard)
    res_b = api_client.post(
        f"/api/resumes/{sample_resume.id}/template/",
        {"template_key": "external-standard"},
        format="json",
    )
    assert res_b.status_code == 200
    assert res_b.json()["changed"] is True

    # Check entries count not modified
    assert SectionEntry.objects.filter(section__resume=sample_resume).count() == initial_entries_count

    # Switch B -> A (external-standard -> iitb-general)
    res_a = api_client.post(
        f"/api/resumes/{sample_resume.id}/template/",
        {"template_key": "iitb-general"},
        format="json",
    )
    assert res_a.status_code == 200
    assert res_a.json()["changed"] is True

    # Assert DB state is identical to start
    sample_resume.refresh_from_db()
    final_sections_snapshot = [
        (s.section_type.key, s.order, s.is_visible, s.entries.count())
        for s in sample_resume.sections.order_by("order")
    ]
    assert final_sections_snapshot == initial_sections_snapshot
    assert SectionEntry.objects.filter(section__resume=sample_resume).count() == initial_entries_count


def test_custom_shuffled_order_preserved(api_client, user, sample_resume, mock_latex):
    api_client.force_authenticate(user=user)

    # Shuffled custom order: reverse current sections order
    sections = list(sample_resume.sections.order_by("order"))
    for idx, s in enumerate(reversed(sections)):
        s.order = idx
        s.save(update_fields=["order"])

    shuffled_keys = [s.section_type.key for s in sample_resume.sections.order_by("order")]

    # Switch to external-standard
    res = api_client.post(
        f"/api/resumes/{sample_resume.id}/template/",
        {"template_key": "external-standard"},
        format="json",
    )
    assert res.status_code == 200

    # Verify that existing shared sections kept their relative order
    post_keys = [s.section_type.key for s in sample_resume.sections.order_by("order")]
    shared_keys = [k for k in post_keys if k in shuffled_keys]
    assert shared_keys == shuffled_keys


def test_hidden_by_switch_and_user_hidden_sections(api_client, user, sample_resume, mock_latex):
    api_client.force_authenticate(user=user)

    # User explicitly hides "technical_skills" which is in both templates
    tech_sec = sample_resume.sections.get(section_type__key="technical_skills")
    tech_sec.is_visible = False
    tech_sec.save(update_fields=["is_visible"])

    # Switch to external-standard
    res = api_client.post(
        f"/api/resumes/{sample_resume.id}/template/",
        {"template_key": "external-standard"},
        format="json",
    )
    assert res.status_code == 200

    # User-hidden section must still be hidden
    tech_sec.refresh_from_db()
    assert tech_sec.is_visible is False

    # Switch back to iitb-general
    res = api_client.post(
        f"/api/resumes/{sample_resume.id}/template/",
        {"template_key": "iitb-general"},
        format="json",
    )
    assert res.status_code == 200

    # User-hidden section must REMAIN hidden
    tech_sec.refresh_from_db()
    assert tech_sec.is_visible is False


def test_style_remap_and_unrelated_config_override_preserved(api_client, user, sample_resume, mock_latex):
    api_client.force_authenticate(user=user)

    # Resume has custom style and custom metadata
    sample_resume.config_override = {
        "style": {"font": "times", "accent": "#1A6B3C"},
        "custom_plugin_data": {"active": True, "score": 99},
    }
    sample_resume.save(update_fields=["config_override"])

    # Switch to awesome-cv-general (font_default: "sourcesans", accent_default: "#DC3522")
    # Style must reset to the target template's authentic original defaults
    res = api_client.post(
        f"/api/resumes/{sample_resume.id}/template/",
        {"template_key": "awesome-cv-general"},
        format="json",
    )
    assert res.status_code == 200
    data = res.json()
    assert data["style"]["font"] == "sourcesans"  # template original default
    assert data["style"]["accent"] == "#DC3522"   # template original default

    sample_resume.refresh_from_db()
    # Unrelated config_override preserved
    assert sample_resume.config_override["custom_plugin_data"] == {"active": True, "score": 99}
    assert "style" not in sample_resume.config_override or not sample_resume.config_override["style"]


def test_switch_template_resets_to_original_defaults_jake(api_client, user, sample_resume, mock_latex):
    api_client.force_authenticate(user=user)

    # Sample resume is on iitb-general (default lmodern, #4B41C8)
    # Dry run should report style reset for accent (since Jake accent default is #000000)
    dry_res = api_client.post(
        f"/api/resumes/{sample_resume.id}/template/",
        {"template_key": "jake-general", "dry_run": True},
        format="json",
    )
    assert dry_res.status_code == 200
    assert "accent" in dry_res.json()["plan"]["style_reset"]

    # Real switch to jake-general
    res = api_client.post(
        f"/api/resumes/{sample_resume.id}/template/",
        {"template_key": "jake-general"},
        format="json",
    )
    assert res.status_code == 200
    data = res.json()
    assert data["style"]["font"] == "lmodern"
    assert data["style"]["accent"] == "#000000"  # Jake classic black


def test_switch_template_spacing_handling(api_client, user, sample_resume, mock_latex):
    api_client.force_authenticate(user=user)

    # Set custom line_spacing and word_spacing
    sample_resume.config_override = {
        "style": {"line_spacing": "1.10", "word_spacing": "1.15"}
    }
    sample_resume.save(update_fields=["config_override"])

    # Switch to awesome-cv-general (which also supports 1.10 and 1.15 in default options)
    res = api_client.post(
        f"/api/resumes/{sample_resume.id}/template/",
        {"template_key": "awesome-cv-general"},
        format="json",
    )
    assert res.status_code == 200
    data = res.json()
    # Spacings are preserved because both templates offer "1.10" and "1.15"
    assert data["style"]["line_spacing"] == "1.10"
    assert data["style"]["word_spacing"] == "1.15"

    sample_resume.refresh_from_db()
    assert sample_resume.config_override["style"]["line_spacing"] == "1.10"
    assert sample_resume.config_override["style"]["word_spacing"] == "1.15"


def test_no_llm_function_called(api_client, user, sample_resume, mock_latex, monkeypatch):
    """Verify that neither GeminiLLMClient nor bullet fitting are called during switch."""
    api_client.force_authenticate(user=user)

    called = {"llm": False, "fitter": False}

    def fake_llm(*args, **kwargs):
        called["llm"] = True
        raise AssertionError("LLM should never be called during template switch")

    def fake_fitter(*args, **kwargs):
        called["fitter"] = True
        raise AssertionError("Bullet fitting should never be called during template switch")

    monkeypatch.setattr("resume_renderer.services.llm_client.GeminiLLMClient.generate_json", fake_llm)
    monkeypatch.setattr("resume_renderer.services.line_fitter.fit_bullets_in_content", fake_fitter)

    res = api_client.post(
        f"/api/resumes/{sample_resume.id}/template/",
        {"template_key": "external-standard"},
        format="json",
    )
    assert res.status_code == 200
    assert not called["llm"]
    assert not called["fitter"]


def test_compile_failure_rolls_back_entire_switch(api_client, user, sample_resume, monkeypatch):
    """If compile_latex fails, the atomic transaction must roll back all DB changes."""
    api_client.force_authenticate(user=user)

    orig_template_id = sample_resume.template_id
    orig_config = copy.deepcopy(sample_resume.config_override)

    monkeypatch.setattr(
        "resumes.services.template_switch.assemble_resume_latex",
        lambda r: "% renderer-v2\n\\dummy{latex}",
    )

    def failing_compile(_):
        raise RuntimeError("Fatal LaTeX compile error: missing package xyz")

    monkeypatch.setattr(
        "resumes.services.template_switch.compile_latex",
        failing_compile,
    )

    res = api_client.post(
        f"/api/resumes/{sample_resume.id}/template/",
        {"template_key": "external-standard"},
        format="json",
    )
    assert res.status_code == 422
    assert "Fatal LaTeX compile error" in res.json()["error"]

    # Verify rollback in DB
    sample_resume.refresh_from_db()
    assert sample_resume.template_id == orig_template_id
    assert sample_resume.config_override == orig_config


# ---------------------------------------------------------------------------
# Docker Integration Test (Skipped when Docker daemon is not running)
# ---------------------------------------------------------------------------

@pytest.mark.docker
@requires_docker
def test_docker_compile_all_templates_and_fonts(user, sample_resume):
    from resume_renderer.services.renderer import compile_latex

    templates = ResumeTemplate.objects.filter(is_active=True)
    for tmpl in templates:
        theme = tmpl.available_themes.first()
        plan = plan_switch(sample_resume, tmpl, theme)
        result = apply_switch(sample_resume, plan)
        assert result["changed"] is True
        assert len(result["pdf"]) > 100

        # Compile with each font offered by this template
        for font_opt in tmpl.template_config.get("font_options", []):
            sample_resume.config_override["style"] = {"font": font_opt}
            sample_resume.save(update_fields=["config_override"])
            latex = assemble_resume_latex(sample_resume)
            pdf_bytes = compile_latex(latex)
            assert pdf_bytes.startswith(b"%PDF")
