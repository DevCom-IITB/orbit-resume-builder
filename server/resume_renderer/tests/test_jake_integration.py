"""
Integration, golden regression, and Docker compile tests for Jake's resume template.
"""
import os
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
from resumes.management.commands.seed_templates import JAKE_PREAMBLE, JAKE_MANIFEST
from resume_renderer.schemas.converter_registry import CONVERTER_SETS, get_converter
from resume_renderer.services.renderer import assemble_resume_latex, compile_latex, _get_docker_client
from resume_renderer.services.styling import FONTS, resolve_style


# ---------------------------------------------------------------------------
# 1. Preamble placeholder tests
# ---------------------------------------------------------------------------
def test_jake_preamble_placeholders():
    """JAKE_PREAMBLE must contain exactly __FONT_SETUP__, __ACCENT_HEX__, __CONTENT__
    and no other __[A-Z0-9_]+__ placeholder."""
    matches = set(re.findall(r"__[A-Z0-9_]+__", JAKE_PREAMBLE))
    assert matches == {"__FONT_SETUP__", "__ACCENT_HEX__", "__CONTENT__", "__SPACING_SETUP__"}


# ---------------------------------------------------------------------------
# 2. Registry & Manifest tests
# ---------------------------------------------------------------------------
def test_jake_converter_set_registered():
    """CONVERTER_SETS['jake-classic'] must contain all 8 section keys."""
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
    assert "jake-classic" in CONVERTER_SETS
    assert set(CONVERTER_SETS["jake-classic"].keys()) == expected_keys
    for k in expected_keys:
        fn = get_converter("jake-classic", k)
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
def test_seed_templates_idempotent_and_creates_jake():
    """Running seed_templates twice should be idempotent and create jake-general."""
    call_command("seed_templates")
    call_command("seed_templates")

    tmpl = ResumeTemplate.objects.get(key="jake-general")
    assert tmpl.display_name == "Jake's Resume"
    assert tmpl.family == "jake"
    assert tmpl.domain == "general"
    assert tmpl.is_active is True

    cfg = tmpl.template_config
    assert cfg["font_default"] == "lmodern"
    assert cfg["font_default"] in FONTS
    for f in cfg["font_options"]:
        assert f in FONTS, f"Font option '{f}' is not in FONTS whitelist."
    assert cfg["accent_default"] == "#000000"
    assert cfg["accent_default"] in cfg["accent_options"]

    theme = tmpl.available_themes.get(key="jake-classic")
    assert theme.converter_set_key == "jake-classic"
    assert "jake" in theme.compatible_families
    assert theme.latex_preamble == JAKE_PREAMBLE

    # Check 8 TemplateSectionType rows in exact manifest order
    tst_rows = list(
        TemplateSectionType.objects.filter(template=tmpl)
        .order_by("default_order")
        .values_list("section_type__key", "is_default", "is_required", "default_order")
    )
    assert len(tst_rows) == 8
    for idx, (expected_key, is_def, is_req, ord_num) in enumerate(JAKE_MANIFEST):
        assert tst_rows[idx] == (expected_key, is_def, is_req, ord_num)


# ---------------------------------------------------------------------------
# 4. Golden tests (assert byte-identical LaTeX against static golden fixtures)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_existing_templates_render_byte_identical_to_golden_fixtures(django_user_model):
    """Verify that iitb-classic, external-standard, and awesome-cv-classic
    render byte-identical LaTeX to the static fixtures captured before changes."""
    call_command("seed_templates")
    user = django_user_model.objects.create_user(username="golden_verifier", password="pw")

    fixtures_dir = os.path.join(os.path.dirname(__file__), "golden_fixtures")

    sample_data = {
        "header": {
            "name": "Jane Doe",
            "degree": "B.Tech.",
            "department": "Computer Science",
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
        "professional_experience": [
            {
                "title": "Software Engineering Intern",
                "organization": "Google",
                "location": "Mountain View, CA",
                "timeline": "May 2024 - Aug 2024",
                "summary": "Core infrastructure team.",
                "bullets": [
                    "Reduced backend latency by 25% through async processing."
                ],
            }
        ],
        "key_projects": [
            {
                "title": "Resume Builder Engine",
                "organization": "Personal Project",
                "timeline": "Jan 2025 - Mar 2025",
                "summary": "Full-stack resume compiler.",
                "bullets": [
                    "Implemented Awesome-CV renderer with dynamic accent colours."
                ],
            }
        ],
        "technical_skills": [
            {
                "category": "Languages",
                "skills": ["Python", "C++", "Go", "TypeScript"],
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
        "courses": [
            {
                "category": "Core Computer Science",
                "courses": ["Data Structures", "Algorithms", "Operating Systems"],
            }
        ],
        "scholastic_achievements": [
            {"text": "All India Rank 42 in JEE Advanced", "year": "2021"}
        ],
    }

    test_configs = [
        ("iitb-general", "iitb-classic", "iitb_classic_golden.tex"),
        ("external-standard", "external-standard", "external_standard_golden.tex"),
        ("awesome-cv-general", "awesome-cv-classic", "awesome_cv_classic_golden.tex"),
    ]

    for tmpl_key, theme_key, fixture_filename in test_configs:
        tmpl = ResumeTemplate.objects.get(key=tmpl_key)
        th = VisualTheme.objects.get(key=theme_key)
        r = Resume.objects.create(
            owner=user,
            title=f"Golden Test {tmpl_key}",
            template=tmpl,
            visual_theme=th,
            config_override={},
        )
        for order, (skey, content) in enumerate(sample_data.items()):
            stdef = SectionTypeDefinition.objects.get(key=skey)
            sec = Section.objects.create(resume=r, section_type=stdef, order=order)
            SectionEntry.objects.create(
                section=sec, generation_status="done", order=0, content=content
            )

        r.latex_cache_valid = False
        actual_latex = assemble_resume_latex(r)

        fixture_path = os.path.join(fixtures_dir, fixture_filename)
        with open(fixture_path, "r", encoding="utf-8") as f:
            expected_latex = f.read()

        assert actual_latex == expected_latex, f"Byte mismatch with golden fixture: {fixture_filename}"


# ---------------------------------------------------------------------------
# 5. Full assemble test for Jake's resume (no leftover placeholders)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
def test_assemble_jake_resume_has_no_leftover_placeholders(django_user_model):
    """Assembling a complete 8-section Jake resume leaves zero placeholders
    and contains \\resumeSubheading."""
    call_command("seed_templates")
    user = django_user_model.objects.create_user(username="jake_tester", password="pw")

    tmpl = ResumeTemplate.objects.get(key="jake-general")
    theme = VisualTheme.objects.get(key="jake-classic")

    resume = Resume.objects.create(
        owner=user,
        title="Full Jake Resume",
        template=tmpl,
        visual_theme=theme,
        config_override={},
    )

    data_by_section = {
        "header": {
            "name": "Jake Gutierrez",
            "degree": "B.S. in Computer Science",
            "department": "Department of EECS",
            "roll_no": "123456",
            "institution": "MIT",
            "email": "jake@example.com",
            "phone": "+1 123 456 7890",
        },
        "education": [
            {
                "examination": "B.S. in Computer Science",
                "institute": "MIT",
                "university": "MIT",
                "year": "2020 - 2024",
                "cpi": "4.9/5.0",
                "note": "Minor in Mathematics",
            }
        ],
        "professional_experience": [
            {
                "title": "Software Engineer",
                "organization": "Acme Inc",
                "location": "Boston, MA",
                "timeline": "2024 - Present",
                "summary": "Full stack infrastructure.",
                "bullets": ["Engineered distributed cache", "Optimized queries"],
            }
        ],
        "key_projects": [
            {
                "title": "Resume Builder",
                "organization": "Open Source",
                "timeline": "2024",
                "bullets": ["Created clean LaTeX template"],
            }
        ],
        "technical_skills": [
            {
                "category": "Languages",
                "skills": ["Python", "C++", "SQL"],
            }
        ],
        "positions_of_responsibility": [
            {
                "role": "Team Lead",
                "organization": "Hackathon Club",
                "duration": "2023",
                "bullets": ["Mentored 20 students"],
            }
        ],
        "courses": [
            {
                "category": "CS Courses",
                "courses": ["Algorithms", "Architecture"],
            }
        ],
        "scholastic_achievements": [
            {"text": "Dean's Honors List", "year": "2023"}
        ],
    }

    for order, (skey, content) in enumerate(data_by_section.items()):
        stdef = SectionTypeDefinition.objects.get(key=skey)
        sec = Section.objects.create(resume=resume, section_type=stdef, order=order)
        SectionEntry.objects.create(section=sec, generation_status="done", order=0, content=content)

    resume.latex_cache_valid = False
    latex_out = assemble_resume_latex(resume)

    assert not re.search(r"__[A-Z0-9_]+__", latex_out)
    assert r"\resumeSubheading" in latex_out
    assert r"\resumeHeader{Jake Gutierrez}" in latex_out
    assert r"\section{Education}" in latex_out
    assert r"\section{Experience}" in latex_out
    assert r"\section{Projects}" in latex_out
    assert r"\section{Technical Skills}" in latex_out
    assert r"\section{Positions of Responsibility}" in latex_out
    assert r"\section{Courses Undertaken}" in latex_out
    assert r"\section{Scholastic Achievements}" in latex_out
    assert r"\end{document}" in latex_out


# ---------------------------------------------------------------------------
# 6. Docker compile tests (all fonts + non-default accent + required edge cases)
# ---------------------------------------------------------------------------
@pytest.mark.docker
@pytest.mark.django_db
def test_jake_compile_in_docker_all_fonts_and_accent(django_user_model):
    """Assemble and compile full Jake resume in Docker.
    Must include:
    - bullet starting with '['
    - '%' and '&' in text
    - an email
    - one entry with empty bullets
    - one project without organization
    And compile with each font in font_options plus one non-default accent."""
    if _get_docker_client() is None:
        pytest.skip("Docker is not available")

    call_command("seed_templates")
    user = django_user_model.objects.create_user(username="jake_docker_tester", password="pw")
    tmpl = ResumeTemplate.objects.get(key="jake-general")
    theme = VisualTheme.objects.get(key="jake-classic")

    resume = Resume.objects.create(
        owner=user,
        title="Docker Edge Cases Jake Resume",
        template=tmpl,
        visual_theme=theme,
        config_override={},
    )

    data_by_section = {
        "header": {
            "name": "Jake Gutierrez",
            "degree": "B.Tech. in Computer Science & Engineering",
            "department": "R&D Department",
            "roll_no": "210050099",
            "institution": "IIT Bombay",
            "email": "jake.gutierrez@example.com",
            "phone": "+1 555 123 4567",
        },
        "education": [
            {
                "examination": "B.Tech. in Computer Science",
                "institute": "IIT Bombay",
                "university": "IIT Bombay",
                "year": "2021 - 2025",
                "cpi": "9.5/10",
                "note": "Top 5% of class",
            }
        ],
        "professional_experience": [
            {
                "title": "Software Engineering Intern",
                "organization": "Acme & Co.",
                "location": "San Francisco, CA",
                "timeline": "Summer 2024",
                "summary": "Core Systems & Infrastructure.",
                "bullets": [
                    "[WIP] Optimized DB query throughput by 35% & reduced tail latency",
                    "Integrated real-time streaming pipelines with 99.9% uptime",
                ],
            },
            {
                "title": "Junior Research Assistant",
                "organization": "Data Labs",
                "location": "Remote",
                "timeline": "2023",
                "summary": "Data cleaning & model benchmarking.",
                "bullets": [],  # entry with empty bullets
            },
        ],
        "key_projects": [
            {
                "title": "Open Source CLI Tool",
                "organization": "",  # project without organization
                "timeline": "Spring 2024",
                "summary": "Automated deployment utility.",
                "bullets": [
                    "[Feature] Built multi-platform binaries using Go & Docker",
                ],
            }
        ],
        "technical_skills": [
            {
                "category": "Languages & Frameworks",
                "skills": ["Python", "C++", "Django", "React & Redux"],
            }
        ],
        "positions_of_responsibility": [
            {
                "role": "Events Lead",
                "organization": "Tech & Coding Club",
                "duration": "2023 - 2024",
                "bullets": ["Managed logistics for annual 50% growth hackathon"],
            }
        ],
        "courses": [
            {
                "category": "Computer Science",
                "courses": ["Data Structures & Algorithms", "Networks & Distributed Systems"],
            }
        ],
        "scholastic_achievements": [
            {"text": "Ranked in top 1% nationally & received merit scholarship", "year": "2021"}
        ],
    }

    for order, (skey, content) in enumerate(data_by_section.items()):
        stdef = SectionTypeDefinition.objects.get(key=skey)
        sec = Section.objects.create(resume=resume, section_type=stdef, order=order)
        SectionEntry.objects.create(section=sec, generation_status="done", order=0, content=content)

    font_options = tmpl.template_config.get("font_options", ["lmodern", "times", "palatino"])
    non_default_accent = "#1F3A5F"

    # 1. Test compilation with each font option
    for font_key in font_options:
        resume.config_override = {"style": {"font": font_key, "accent": "#000000"}}
        resume.latex_cache_valid = False
        latex_text = assemble_resume_latex(resume)
        pdf_bytes = compile_latex(latex_text)
        assert pdf_bytes.startswith(b"%PDF"), f"Compile failed for font '{font_key}'"

    # 2. Test compilation with non-default accent #1F3A5F
    resume.config_override = {"style": {"font": "lmodern", "accent": non_default_accent}}
    resume.latex_cache_valid = False
    latex_text = assemble_resume_latex(resume)
    pdf_bytes = compile_latex(latex_text)
    assert pdf_bytes.startswith(b"%PDF"), f"Compile failed for non-default accent '{non_default_accent}'"
