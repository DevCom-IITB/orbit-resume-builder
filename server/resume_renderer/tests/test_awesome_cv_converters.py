import re
import pytest
from resume_renderer.schemas.converters import awesome_cv as c


def balanced(s):
    s = re.sub(r"\\[{}]", "", s)
    return s.count("{") == s.count("}")


def test_experience_omits_empty_cvitems():
    out = c.convert_experience([{"title": "Intern", "organization": "Acme", "timeline": "2025"}])
    assert "cvitems" not in out and out.count(r"\cventry") == 1 and balanced(out)


def test_bullet_starting_with_bracket_is_braced():
    out = c.convert_experience([{"title": "A", "organization": "B", "timeline": "C",
                                 "bullets": ["[WIP] built API"]}])
    assert r"\item {[WIP] built API}" in out


def test_header_five_args_and_email_link():
    out = c.convert_header({"name": "Asha Rao Iyer", "email": "a.b@x.com", "phone": "+91 99",
                            "degree": "B.Tech.", "department": "CSE", "roll_no": "123"})
    assert out.startswith(r"\cvheader{Asha Rao}{Iyer}") and r"\href{mailto:a.b@x.com}" in out
    assert balanced(out)


def test_scholastic_year_optional():
    out = c.convert_scholastic_achievements(["AIR 123", {"text": "Rank 1", "year": "2022"}])
    assert r"\cvhonor{}{AIR 123}{}{}" in out and r"\cvhonor{}{Rank 1}{}{2022}" in out


def test_empty_sections_return_empty_string():
    assert c.convert_technical_skills([]) == "" and c.convert_education([]) == ""
    assert c.convert_courses([]) == ""
    assert c.convert_experience([]) == ""
    assert c.convert_key_project([]) == ""
    assert c.convert_pors([]) == ""
    assert c.convert_scholastic_achievements([]) == ""


def test_header_single_word_name():
    out = c.convert_header({"name": "Cher", "email": "cher@example.com"})
    assert out.startswith(r"\cvheader{Cher}{}")


def test_header_missing_name_raises():
    with pytest.raises(ValueError, match="Missing key in header data: 'name'"):
        c.convert_header({"email": "foo@bar.com"})


def test_header_non_dict_raises():
    with pytest.raises(ValueError, match="Header must be a dictionary"):
        c.convert_header(["not", "a", "dict"])


def test_experience_happy_path_with_summary_and_bullets():
    data = [
        {
            "title": "Software Engineer",
            "organization": "Google",
            "location": "Mountain View, CA",
            "timeline": "2024 - Present",
            "summary": "Core search ranking infrastructure.",
            "bullets": ["Optimized query parsing latency by 15%", "Designed streaming pipeline"],
        }
    ]
    out = c.convert_experience(data)
    assert r"\cvsection{Professional Experience}" in out
    assert r"\begin{cventries}" in out
    assert r"\cvsummary{Core search ranking infrastructure.}" in out
    assert r"\begin{cvitems}" in out
    assert r"\item {Optimized query parsing latency by 15\%}" in out
    assert r"\item {Designed streaming pipeline}" in out
    assert r"\end{cvitems}" in out
    assert r"\end{cventries}" in out
    assert balanced(out)


def test_key_project_happy_path():
    data = [
        {
            "title": "Orbit Resume Builder",
            "organization": "Open Source",
            "timeline": "Spring 2026",
            "summary": "LaTeX and Django based platform.",
            "bullets": ["Implemented Awesome-CV renderer"],
        }
    ]
    out = c.convert_key_project(data)
    assert r"\cvsection{Key Projects}" in out
    assert r"\cventry" in out
    assert r"\item {Implemented Awesome-CV renderer}" in out
    assert balanced(out)


def test_pors_happy_path():
    data = [
        {
            "role": "Lead Coordinator",
            "organization": "Tech Fest",
            "duration": "2025 - 2026",
            "bullets": ["Managed 50 volunteers"],
        }
    ]
    out = c.convert_pors(data)
    assert r"\cvsection{Positions of Responsibility}" in out
    assert r"\cventry" in out
    assert "Lead Coordinator" in out
    assert "Tech Fest" in out
    assert balanced(out)


def test_education_happy_path():
    data = [
        {
            "examination": "B.Tech. in Computer Science",
            "institute": "IIT Bombay",
            "university": "IIT Bombay",
            "year": "2022 - 2026",
            "cpi": "9.5/10",
            "note": "Minor in Data Science",
        }
    ]
    out = c.convert_education(data)
    assert r"\cvsection{Education}" in out
    assert r"\cventry" in out
    assert r"\item {CPI/Score: 9.5/10}" in out
    assert r"\item {Minor in Data Science}" in out
    assert balanced(out)


def test_education_only_university_fallback():
    data = [
        {
            "examination": "High School",
            "institute": "",
            "university": "State Board",
            "year": "2022",
        }
    ]
    out = c.convert_education(data)
    assert "State Board" in out
    assert balanced(out)


def test_technical_skills_happy_path():
    data = [
        {
            "category": "Languages",
            "skills": ["Python", "C++", "TypeScript"],
            "note": "Proficient",
        },
        {
            "category": "Frameworks",
            "skills": ["Django", "React"],
        },
    ]
    out = c.convert_technical_skills(data)
    assert r"\cvsection{Technical Skills}" in out
    assert r"\begin{cvskills}" in out
    assert r"\cvskill{Languages}{Python, C++, TypeScript \textit{Proficient}}" in out
    assert r"\cvskill{Frameworks}{Django, React}" in out
    assert r"\end{cvskills}" in out
    assert balanced(out)


def test_courses_happy_path():
    data = [
        {
            "category": "Computer Science",
            "courses": ["Data Structures", "Algorithms", "Operating Systems"],
        }
    ]
    out = c.convert_courses(data)
    assert r"\cvsection{Courses Undertaken}" in out
    assert r"\cvskill{Computer Science}{Data Structures, Algorithms, Operating Systems}" in out
    assert balanced(out)


def test_validation_errors():
    with pytest.raises(ValueError, match="Input must be a list of experience entries"):
        c.convert_experience("invalid")

    with pytest.raises(ValueError, match="Each experience entry must be a dictionary"):
        c.convert_experience(["not-a-dict"])

    with pytest.raises(ValueError, match="Missing key in experience data: 'title'"):
        c.convert_experience([{"organization": "Acme"}])

    with pytest.raises(ValueError, match="'bullets' must be a list"):
        c.convert_experience([{"title": "Dev", "bullets": "not-a-list"}])

    with pytest.raises(ValueError, match="Input must be a list of education entries"):
        c.convert_education("not-a-list")

    with pytest.raises(ValueError, match="Input must be a list of achievements"):
        c.convert_scholastic_achievements("not-a-list")

    with pytest.raises(ValueError, match="Each achievement must be a string or dict"):
        c.convert_scholastic_achievements([12345])

    with pytest.raises(ValueError, match="Input must be a list of skill categories"):
        c.convert_technical_skills("invalid")
