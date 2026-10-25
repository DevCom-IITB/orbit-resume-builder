import re
import pytest
from django.core.management import call_command

from resumes.models import (
    Resume,
    ResumeTemplate,
    Section,
    SectionEntry,
    SectionTypeDefinition,
    VisualTheme,
)
from resumes.management.commands.seed_templates import IITB_PREAMBLE
from resume_renderer.schemas.converters import (
    convert_courses,
    convert_education,
    convert_experience,
    convert_header,
    convert_key_project,
    convert_pors,
    convert_scholastic_achievements,
    convert_technical_skills,
)
from resume_renderer.schemas.converters.iitb_layout import (
    ENTRY_GAP_PT,
    HEADER_GAP_PT,
    LIST_SECTION_END_GAP_PT,
    SCHOLASTIC_END_GAP_PT,
    TABLE_SECTION_END_GAP_PT,
    vspace,
)
from resume_renderer.services.renderer import (
    _get_docker_client,
    assemble_resume_latex,
    compile_latex,
)


def _balanced_braces(s: str) -> bool:
    no_linebreaks = s.replace(r"\\", "")
    clean = re.sub(r"\\[{}]", "", no_linebreaks)
    return clean.count("{") == clean.count("}")


def _matching_environments(s: str) -> bool:
    begins = re.findall(r"\\begin\{([^}]+)\}", s)
    ends = re.findall(r"\\end\{([^}]+)\}", s)
    return sorted(begins) == sorted(ends)


# ---------------------------------------------------------------------------
# 1. Converter Unit Tests
# ---------------------------------------------------------------------------

def test_header_ends_with_minipage_blank_line_and_vspace():
    data = {
        "name": "Jane Doe",
        "roll_no": "210050001",
        "department": "Computer Science",
        "degree": "B.Tech.",
        "institution": "IIT Bombay",
        "email": "jane@example.com",
        "phone": "+91 9876543210",
    }
    out = convert_header.convert_header(data)
    expected_end = r"\end{minipage}" + "\n\n" + vspace(HEADER_GAP_PT) + "\n"
    assert out.endswith(expected_end)
    assert _balanced_braces(out)


def test_scholastic_ends_with_gap():
    achievements = [
        {"text": "Rank 1 in JEE", "year": "2021"},
        "Olympiad Gold Medalist",
    ]
    out = convert_scholastic_achievements.convert_scholastic_achievements(achievements)
    expected_end = r"\end{itemize}" + "\n" + vspace(SCHOLASTIC_END_GAP_PT)
    assert out.endswith(expected_end)
    assert r"\section*{\color{myblue}{\large SCHOLASTIC ACHIEVEMENTS}" in out
    assert _balanced_braces(out)


def test_experience_two_entries_and_single_entry_gaps():
    entries = [
        {
            "title": "Intern 1",
            "organization": "Company 1",
            "timeline": "Summer 2024",
            "bullets": ["Did work 1"],
        },
        {
            "title": "Intern 2",
            "organization": "Company 2",
            "timeline": "Summer 2025",
            "bullets": ["Did work 2"],
        },
    ]
    out = convert_experience.convert_experience(entries)
    # First entry followed by ENTRY_GAP_PT
    first_end = r"\end{itemize}" + "\n" + vspace(ENTRY_GAP_PT)
    # Last entry followed by LIST_SECTION_END_GAP_PT
    last_end = r"\end{itemize}" + "\n" + vspace(LIST_SECTION_END_GAP_PT)
    assert first_end in out
    assert out.endswith(last_end)

    # Single entry gets LIST_SECTION_END_GAP_PT
    single_out = convert_experience.convert_experience([entries[0]])
    assert single_out.endswith(last_end)
    assert vspace(ENTRY_GAP_PT) not in single_out


def test_key_projects_two_entries_and_single_entry_gaps():
    projects = [
        {
            "title": "Project A",
            "organization": "Org A",
            "timeline": "2024",
            "summary": "Summary A",
            "bullets": ["Feature 1", "Feature 2"],
        },
        {
            "title": "Project B",
            "organization": "Org B",
            "timeline": "2025",
            "summary": "Summary B",
            "bullets": ["Feature 3"],
        },
    ]
    out = convert_key_project.convert_key_project(projects)
    first_end = r"\end{itemize}" + "\n" + vspace(ENTRY_GAP_PT)
    last_end = r"\end{itemize}" + "\n" + vspace(LIST_SECTION_END_GAP_PT)
    assert first_end in out
    assert out.endswith(last_end)

    single_out = convert_key_project.convert_key_project([projects[0]])
    assert single_out.endswith(last_end)
    assert vspace(ENTRY_GAP_PT) not in single_out


def test_pors_two_entries_and_single_entry_gaps():
    pors = [
        {
            "role": "Role 1",
            "organization": "Org 1",
            "duration": "2024",
            "bullets": ["Bullet 1"],
        },
        {
            "role": "Role 2",
            "organization": "Org 2",
            "duration": "2025",
            "bullets": ["Bullet 2"],
        },
    ]
    out = convert_pors.convert_pors(pors)
    first_end = r"\end{itemize}" + "\n" + vspace(ENTRY_GAP_PT)
    last_end = r"\end{itemize}" + "\n" + vspace(LIST_SECTION_END_GAP_PT)
    assert first_end in out
    assert out.endswith(last_end)
    assert "itemsep = -0.80 mm" in out


def test_entry_without_bullets_guard():
    """Entries without bullets must NOT emit an empty itemize or summary trailing linebreaks."""
    entry_no_bullets = [
        {
            "title": "Standalone Project",
            "organization": "Self",
            "timeline": "2025",
            "summary": "Project summary without bullets",
            "bullets": ["", "   "],
        }
    ]
    out = convert_key_project.convert_key_project(entry_no_bullets)
    assert r"\begin{itemize}" not in out
    assert r"\end{itemize}" not in out
    # Summary line does not have trailing \\ or trailing \vspace
    assert r"{\it Project summary without bullets}\\" not in out
    assert r"{\it Project summary without bullets}" in out
    assert out.endswith(vspace(LIST_SECTION_END_GAP_PT))

    # Same check for experience
    exp_out = convert_experience.convert_experience([
        {
            "title": "Consultant",
            "organization": "Firm",
            "timeline": "2024",
            "summary": "High-level advisory",
            "bullets": [],
        }
    ])
    assert r"\begin{itemize}" not in exp_out
    assert r"\end{itemize}" not in exp_out
    assert r"{\it High-level advisory}\\" not in exp_out
    assert r"{\it High-level advisory}" in exp_out
    assert exp_out.endswith(vspace(LIST_SECTION_END_GAP_PT))


def test_technical_skills_and_courses_end_with_gap():
    skills = [{"category": "Languages", "skills": ["Python", "Rust"]}]
    skills_out = convert_technical_skills.convert_technical_skills(skills)
    assert skills_out.endswith(r"\end{tabular}" + "\n" + vspace(TABLE_SECTION_END_GAP_PT))

    courses = [{"category": "CS", "courses": ["Algorithms", "OS"]}]
    courses_out = convert_courses.convert_courses(courses)
    assert courses_out.endswith(r"\end{tabular}" + "\n" + vspace(TABLE_SECTION_END_GAP_PT))


def test_education_remains_unchanged():
    edu = [
        {
            "examination": "B.Tech.",
            "university": "IIT",
            "institute": "IITB",
            "year": "2025",
            "cpi": "9.5",
        }
    ]
    out = convert_education.convert_education(edu)
    assert out.endswith(r"\end{tabularx}")
    assert vspace(LIST_SECTION_END_GAP_PT) not in out


def test_spacing_operation_scales_gap_between_blocks():
    """Line spacing '+' operation increases the gap between entries."""
    projects = [
        {"title": "rag chatbot", "organization": "self project", "bullets": ["b1"]},
        {"title": "openfema forecaster project", "organization": "self project", "bullets": ["b2"]},
    ]
    # Default line spacing (1.00)
    out_100 = convert_key_project.convert_key_project(projects, {"style": {"line_spacing": "1.00"}})
    assert vspace(ENTRY_GAP_PT) in out_100
    assert r"\vspace{-4pt}" in out_100

    # Line spacing 1.05 (+1 step: +2pt)
    out_105 = convert_key_project.convert_key_project(projects, {"style": {"line_spacing": "1.05"}})
    assert r"\vspace{-2pt}" in out_105

    # Line spacing 1.10 (+2 steps: +4pt => 0pt, omitted)
    out_110 = convert_key_project.convert_key_project(projects, {"style": {"line_spacing": "1.10"}})
    assert r"\vspace{-4pt}" not in out_110
    assert r"\vspace{0pt}" not in out_110

    # Line spacing 1.15 (+3 steps: +6pt => +2pt)
    out_115 = convert_key_project.convert_key_project(projects, {"style": {"line_spacing": "1.15"}})
    assert r"\vspace{2pt}" in out_115


# ---------------------------------------------------------------------------
# 2. Preamble Tests
# ---------------------------------------------------------------------------

def test_preamble_structure_and_placeholders():
    assert IITB_PREAMBLE.count("__FONT_SETUP__") == 1
    assert IITB_PREAMBLE.count("__ACCENT_HEX__") == 1
    assert IITB_PREAMBLE.count("__SPACING_SETUP__") == 1
    assert IITB_PREAMBLE.count("__CONTENT__") == 1
    assert re.findall(r"__[A-Z0-9_]+__", IITB_PREAMBLE) == [
        "__FONT_SETUP__",
        "__ACCENT_HEX__",
        "__SPACING_SETUP__",
        "__CONTENT__",
    ]
    assert r"\titleformat{\section}{\scshape\raggedright}{}{0em}{}" in IITB_PREAMBLE
    assert r"\input{bk#1.clo}" in IITB_PREAMBLE
    assert r"\fontsize{#1}{\baselineskip}" not in IITB_PREAMBLE
    assert "__SPACING_SETUP__\\begin{document}" in IITB_PREAMBLE


# ---------------------------------------------------------------------------
# 3. Lint Tests on Full Assembled Resume
# ---------------------------------------------------------------------------

@pytest.fixture
def rich_resume_data():
    return {
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


@pytest.mark.django_db
def test_full_assembled_latex_lint(django_user_model, rich_resume_data):
    call_command("seed_templates")
    user = django_user_model.objects.create_user(username="lint_tester", password="pw")
    tmpl = ResumeTemplate.objects.get(key="iitb-general")
    theme = VisualTheme.objects.get(key="iitb-classic")

    resume = Resume.objects.create(
        owner=user,
        title="Lint Resume",
        template=tmpl,
        visual_theme=theme,
        config_override={},
    )
    for order, (skey, content) in enumerate(rich_resume_data.items()):
        stdef = SectionTypeDefinition.objects.get(key=skey)
        sec = Section.objects.create(resume=resume, section_type=stdef, order=order)
        SectionEntry.objects.create(
            section=sec, generation_status="done", order=0, content=content
        )

    latex = assemble_resume_latex(resume)

    # 1. No empty itemize
    assert not re.search(r"\\begin\{itemize\}[^\]]*\]\s*\\end\{itemize\}", latex)
    # 2. No consecutive line breaks
    assert not re.search(r"\\\\(?:\s*\\\\)+", latex)
    # 3. No vspace{0pt}
    assert r"\vspace{0pt}" not in latex
    # 4. Balanced braces
    assert _balanced_braces(latex)
    # 5. Matching environments
    assert _matching_environments(latex)
    # 6. No leftover placeholders
    assert not re.search(r"__[A-Z0-9_]+__", latex)


# ---------------------------------------------------------------------------
# 4. Docker Compilation & Glyph Tests
# ---------------------------------------------------------------------------

@pytest.mark.docker
@pytest.mark.django_db
def test_docker_compile_all_fonts_and_spacing_extremes(django_user_model, rich_resume_data):
    if _get_docker_client() is None:
        pytest.skip("Docker is not available")

    call_command("seed_templates")
    user = django_user_model.objects.create_user(username="docker_tester", password="pw")

    fonts = ["lmodern", "times", "palatino"]
    spacings = [("0.90", "0.90"), ("1.20", "1.20")]

    for theme_key, tmpl_key in [("iitb-classic", "iitb-general"), ("external-standard", "external-standard")]:
        tmpl = ResumeTemplate.objects.get(key=tmpl_key)
        th = VisualTheme.objects.get(key=theme_key)

        for font in fonts:
            for line_sp, word_sp in spacings:
                resume = Resume.objects.create(
                    owner=user,
                    title=f"Docker Test {theme_key} {font}",
                    template=tmpl,
                    visual_theme=th,
                    config_override={
                        "style": {
                            "font": font,
                            "line_spacing": line_sp,
                            "word_spacing": word_sp,
                        }
                    },
                )
                for order, (skey, content) in enumerate(rich_resume_data.items()):
                    stdef = SectionTypeDefinition.objects.get(key=skey)
                    sec = Section.objects.create(resume=resume, section_type=stdef, order=order)
                    SectionEntry.objects.create(
                        section=sec, generation_status="done", order=0, content=content
                    )

                latex = assemble_resume_latex(resume)
                pdf_bytes = compile_latex(latex)
                assert pdf_bytes.startswith(b"%PDF"), f"Compile failed for {theme_key} {font} {line_sp}/{word_sp}"


@pytest.mark.docker
@pytest.mark.django_db
def test_docker_glyph_rendering_t1(django_user_model):
    """Verify that <, >, and | render as actual ASCII characters in PDF rather than ¡ or ¿."""
    if _get_docker_client() is None:
        pytest.skip("Docker is not available")

    import fitz  # PyMuPDF

    call_command("seed_templates")
    user = django_user_model.objects.create_user(username="glyph_tester", password="pw")
    tmpl = ResumeTemplate.objects.get(key="iitb-general")
    theme = VisualTheme.objects.get(key="iitb-classic")

    resume = Resume.objects.create(
        owner=user,
        title="Glyph Test Resume",
        template=tmpl,
        visual_theme=theme,
        config_override={},
    )
    # Add header
    st_header = SectionTypeDefinition.objects.get(key="header")
    sec_header = Section.objects.create(resume=resume, section_type=st_header, order=0)
    SectionEntry.objects.create(
        section=sec_header,
        generation_status="done",
        order=0,
        content={
            "name": "Jane Doe",
            "degree": "B.Tech.",
            "department": "CSE",
            "roll_no": "210050001",
            "institution": "IIT Bombay",
            "email": "jane@example.com",
            "phone": "+91 9876543210",
        },
    )

    # Add experience with glyphs
    st_exp = SectionTypeDefinition.objects.get(key="professional_experience")
    sec_exp = Section.objects.create(resume=resume, section_type=st_exp, order=1)
    SectionEntry.objects.create(
        section=sec_exp,
        generation_status="done",
        order=0,
        content=[
            {
                "title": "Software Engineer",
                "organization": "Acme",
                "timeline": "2025",
                "bullets": [
                    "Engineered pipeline with threshold < 10ms and throughput > 5000 req/s | verified."
                ],
            }
        ],
    )

    latex = assemble_resume_latex(resume)
    pdf_bytes = compile_latex(latex)

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    full_text = "".join(page.get_text() for page in doc)

    assert "<" in full_text, "Expected '<' in rendered PDF text"
    assert ">" in full_text, "Expected '>' in rendered PDF text"
    assert "|" in full_text, "Expected '|' in rendered PDF text"
    assert "¡" not in full_text, "Unexpected Spanish inverted exclamation '¡' in PDF text"
    assert "¿" not in full_text, "Unexpected Spanish inverted question mark '¿' in PDF text"
