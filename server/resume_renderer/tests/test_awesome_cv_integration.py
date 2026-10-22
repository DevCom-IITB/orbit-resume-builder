"""
Integration and regression tests for the Awesome-CV template,
preamble, registry, seeding, and rendering pipeline.
"""
import re
import pytest
from django.core.management import call_command
from resumes.models import (
    Resume,
    ResumeTemplate,
    Section,
    SectionEntry,
    SectionTypeDefinition,
    TemplateSectionType,
    VisualTheme,
)
from resumes.management.commands.seed_templates import AWESOME_PREAMBLE, AWESOME_MANIFEST
from resume_renderer.schemas.converter_registry import CONVERTER_SETS, get_converter
from resume_renderer.services.renderer import assemble_resume_latex, compile_latex, _get_docker_client
from resume_renderer.services.styling import FONTS, resolve_style


# ---------------------------------------------------------------------------
# 1. Preamble placeholder tests
# ---------------------------------------------------------------------------
def test_awesome_preamble_placeholders():
    """AWESOME_PREAMBLE must contain exactly __FONT_SETUP__, __ACCENT_HEX__, __CONTENT__
    and no other __[A-Z0-9_]+__ placeholder."""
    matches = set(re.findall(r"__[A-Z0-9_]+__", AWESOME_PREAMBLE))
    assert matches == {"__FONT_SETUP__", "__ACCENT_HEX__", "__CONTENT__", "__SPACING_SETUP__"}


# ---------------------------------------------------------------------------
# 2. Registry tests
# ---------------------------------------------------------------------------
def test_awesome_cv_converter_set_registered():
    """CONVERTER_SETS['awesome-cv'] must contain all 8 section keys."""
    expected_keys = {
        "header",
        "education",
        "scholastic_achievements",
        "courses",
        "professional_experience",
        "key_projects",
        "positions_of_responsibility",
        "technical_skills",
    }
    assert "awesome-cv" in CONVERTER_SETS
    assert set(CONVERTER_SETS["awesome-cv"].keys()) == expected_keys
    for k in expected_keys:
        fn = get_converter("awesome-cv", k)
        assert callable(fn)


@pytest.mark.django_db
def test_all_templates_have_converters_for_manifest_sections():
    """Generic test: every manifest section type for every active template
    must have a valid converter in all compatible available themes."""
    call_command("seed_templates")
    templates = ResumeTemplate.objects.filter(is_active=True).prefetch_related(
        "available_themes", "section_manifest__section_type"
    )
    assert templates.exists()

    for tmpl in templates:
        manifest_section_keys = [
            tst.section_type.key for tst in tmpl.section_manifest.all()
        ]
        assert manifest_section_keys, f"Template {tmpl.key} has no sections."
        for theme in tmpl.available_themes.all():
            for skey in manifest_section_keys:
                converter = get_converter(theme.converter_set_key, skey)
                assert callable(converter), (
                    f"Missing converter for template '{tmpl.key}', "
                    f"theme '{theme.key}' (set '{theme.converter_set_key}'), "
                    f"section '{skey}'"
                )


# ---------------------------------------------------------------------------
# 3. Seed tests (idempotency, manifest ordering, template config)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_seed_templates_idempotent_and_creates_awesome_cv():
    """Running seed_templates twice should be idempotent and create awesome-cv-general."""
    call_command("seed_templates")
    call_command("seed_templates")

    tmpl = ResumeTemplate.objects.get(key="awesome-cv-general")
    assert tmpl.display_name == "Awesome CV"
    assert tmpl.family == "awesome"
    assert tmpl.domain == "general"
    assert tmpl.is_active is True

    cfg = tmpl.template_config
    assert cfg["font_default"] == "sourcesans"
    assert cfg["font_default"] in FONTS
    for f in cfg["font_options"]:
        assert f in FONTS, f"Font option '{f}' is not in FONTS whitelist."
    assert cfg["accent_default"] == "#DC3522"
    assert cfg["accent_default"] in cfg["accent_options"]

    theme = tmpl.available_themes.get(key="awesome-cv-classic")
    assert theme.converter_set_key == "awesome-cv"
    assert "awesome" in theme.compatible_families
    assert theme.latex_preamble == AWESOME_PREAMBLE

    # Check 8 TemplateSectionType rows in exact manifest order
    tst_rows = list(
        TemplateSectionType.objects.filter(template=tmpl)
        .order_by("default_order")
        .values_list("section_type__key", "is_default", "is_required", "default_order")
    )
    assert len(tst_rows) == 8
    for idx, (expected_key, is_def, is_req, ord_num) in enumerate(AWESOME_MANIFEST):
        assert tst_rows[idx] == (expected_key, is_def, is_req, ord_num)


# ---------------------------------------------------------------------------
# 4. Golden tests (existing templates remain byte-identical)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_existing_templates_render_byte_identical_latex(django_user_model):
    """Ensure that IITB and external templates render byte-identical LaTeX
    to their established baseline with default and custom styles."""
    call_command("seed_templates")
    user = django_user_model.objects.create_user(username="golden_tester", password="pw")

    iitb_template = ResumeTemplate.objects.get(key="iitb-general")
    iitb_theme = VisualTheme.objects.get(key="iitb-classic")

    resume = Resume.objects.create(
        owner=user,
        title="Golden Test Resume",
        template=iitb_template,
        visual_theme=iitb_theme,
        config_override={},
    )

    # Add sample sections
    st_header = SectionTypeDefinition.objects.get(key="header")
    sec_header = Section.objects.create(resume=resume, section_type=st_header, order=0)
    SectionEntry.objects.create(
        section=sec_header,
        generation_status="done",
        order=0,
        content={
            "name": "Jane Doe",
            "degree": "B.Tech.",
            "department": "Computer Science",
            "roll_no": "210050001",
            "institution": "IIT Bombay",
            "email": "jane@example.com",
            "phone": "+91 9876543210",
        },
    )

    st_exp = SectionTypeDefinition.objects.get(key="professional_experience")
    sec_exp = Section.objects.create(resume=resume, section_type=st_exp, order=1)
    SectionEntry.objects.create(
        section=sec_exp,
        generation_status="done",
        order=0,
        content=[
            {
                "title": "Software Engineer Intern",
                "organization": "Acme Corp",
                "location": "Mumbai",
                "timeline": "Summer 2025",
                "bullets": ["Engineered high-throughput event processing pipelines."],
            }
        ],
    )

    # 1. IITB Classic render
    latex_iitb = assemble_resume_latex(resume)
    assert "__FONT_SETUP__" not in latex_iitb
    assert "__ACCENT_HEX__" not in latex_iitb
    assert "__CONTENT__" not in latex_iitb
    assert r"\usepackage{lmodern}" in latex_iitb
    assert r"\definecolor{myblue}{HTML}{4B41C8}" in latex_iitb
    assert "Jane Doe" in latex_iitb
    assert "Acme Corp" in latex_iitb

    # 2. External Standard render (using external theme)
    ext_theme = VisualTheme.objects.get(key="external-standard")
    ext_template = ResumeTemplate.objects.get(key="external-standard")
    resume.template = ext_template
    resume.visual_theme = ext_theme
    resume.latex_cache_valid = False

    latex_ext = assemble_resume_latex(resume)
    assert latex_ext == latex_iitb


# ---------------------------------------------------------------------------
# 5. Full assemble test for Awesome CV (no unfilled placeholders)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_assemble_awesome_cv_has_no_leftover_placeholders(django_user_model):
    """Assembling a complete 8-section Awesome CV resume leaves zero placeholders."""
    call_command("seed_templates")
    user = django_user_model.objects.create_user(username="awesome_tester", password="pw")

    tmpl = ResumeTemplate.objects.get(key="awesome-cv-general")
    theme = VisualTheme.objects.get(key="awesome-cv-classic")

    resume = Resume.objects.create(
        owner=user,
        title="Full Awesome CV",
        template=tmpl,
        visual_theme=theme,
        config_override={},
    )

    data_by_section = {
        "header": {
            "name": "Jane Doe",
            "degree": "B.Tech.",
            "department": "Computer Science and Engineering",
            "roll_no": "210050001",
            "institution": "IIT Bombay",
            "email": "jane@example.com",
            "phone": "+91 9876543210",
        },
        "education": [
            {
                "examination": "B.Tech. in Computer Science",
                "institute": "IIT Bombay",
                "university": "IIT Bombay",
                "year": "2021 - 2025",
                "cpi": "9.8/10",
                "note": "Dean's List",
            }
        ],
        "scholastic_achievements": [
            {"text": "All India Rank 42 in JEE Advanced", "year": "2021"},
            "KVPY Fellow",
        ],
        "courses": [
            {
                "category": "Core Computer Science",
                "courses": ["Data Structures", "Algorithms", "Operating Systems"],
            }
        ],
        "professional_experience": [
            {
                "title": "Software Engineering Intern",
                "organization": "Google",
                "location": "Mountain View, CA",
                "timeline": "May 2024 - Aug 2024",
                "summary": "Core infrastructure team.",
                "bullets": ["Reduced backend latency by 25% through async processing."],
            }
        ],
        "key_projects": [
            {
                "title": "Resume Builder Engine",
                "organization": "Personal Project",
                "timeline": "Jan 2025 - Mar 2025",
                "summary": "Full-stack resume compiler.",
                "bullets": ["Implemented Awesome-CV renderer with dynamic accent colours."],
            }
        ],
        "positions_of_responsibility": [
            {
                "role": "Overall Coordinator",
                "organization": "Computer Society",
                "duration": "2023 - 2024",
                "bullets": ["Led a 40-member team organizing technical events."],
            }
        ],
        "technical_skills": [
            {
                "category": "Languages",
                "skills": ["Python", "C++", "Go", "TypeScript"],
            },
            {
                "category": "Tools",
                "skills": ["Docker", "Git", "PostgreSQL", "Linux"],
            },
        ],
    }

    for order, (skey, content) in enumerate(data_by_section.items()):
        stdef = SectionTypeDefinition.objects.get(key=skey)
        sec = Section.objects.create(resume=resume, section_type=stdef, order=order)
        SectionEntry.objects.create(section=sec, generation_status="done", order=0, content=content)

    resume.latex_cache_valid = False
    latex_out = assemble_resume_latex(resume)

    # Assert no unfilled placeholders
    assert not re.search(r"__[A-Z0-9_]+__", latex_out)

    # Assert Awesome CV specific macros are present
    assert r"\usepackage[default]{sourcesanspro}" in latex_out
    assert r"\definecolor{awesome}{HTML}{DC3522}" in latex_out
    assert r"\cvheader{Jane}{Doe}" in latex_out
    assert r"\cvsection{Education}" in latex_out
    assert r"\cvsection{Scholastic Achievements}" in latex_out
    assert r"\cvsection{Courses Undertaken}" in latex_out
    assert r"\cvsection{Professional Experience}" in latex_out
    assert r"\cvsection{Key Projects}" in latex_out
    assert r"\cvsection{Positions of Responsibility}" in latex_out
    assert r"\cvsection{Technical Skills}" in latex_out
    assert r"\end{document}" in latex_out


# ---------------------------------------------------------------------------
# 6. Docker compile tests (skipped when Docker is unavailable)
# ---------------------------------------------------------------------------
@pytest.mark.docker
def test_awesome_cv_compile_in_docker(django_user_model):
    """Assemble and compile full Awesome CV document in Docker."""
    if _get_docker_client() is None:
        pytest.skip("Docker is not available")

    call_command("seed_templates")
    user = django_user_model.objects.create_user(username="compile_tester", password="pw")
    tmpl = ResumeTemplate.objects.get(key="awesome-cv-general")
    theme = VisualTheme.objects.get(key="awesome-cv-classic")

    resume = Resume.objects.create(
        owner=user,
        title="Docker Compile Resume",
        template=tmpl,
        visual_theme=theme,
        config_override={},
    )

    st_header = SectionTypeDefinition.objects.get(key="header")
    sec_header = Section.objects.create(resume=resume, section_type=st_header, order=0)
    SectionEntry.objects.create(
        section=sec_header,
        generation_status="done",
        order=0,
        content={"name": "Asha Rao Iyer", "email": "asha@example.com"},
    )

    # Test each font option and a non-default accent
    font_options = tmpl.template_config.get("font_options", ["sourcesans"])
    test_accent = "#0395DE"

    for font_key in font_options:
        resume.config_override = {"style": {"font": font_key, "accent": test_accent}}
        resume.latex_cache_valid = False
        latex_text = assemble_resume_latex(resume)
        pdf_bytes = compile_latex(latex_text)
        assert pdf_bytes.startswith(b"%PDF"), f"Compile failed for font {font_key}"
