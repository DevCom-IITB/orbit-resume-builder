import re
import pytest
from resume_renderer.schemas.converters import jake as j


def squash(s):
    return re.sub(r"\s+", "", s)


def balanced(s):
    s = re.sub(r"\\[{}]", "", s)
    return s.count("{") == s.count("}")


def test_experience_arg_order_and_nesting():
    out = j.convert_experience([{"title": "Intern", "organization": "Acme",
                                 "location": "Mumbai", "timeline": "2025",
                                 "bullets": ["Built API"]}])
    assert r"\resumeSubheading{Intern}{2025}{Acme}{Mumbai}" in squash(out)
    assert out.index(r"\resumeSubHeadingListStart") < out.index(r"\resumeItemListStart")
    assert balanced(out)


def test_no_empty_item_list():
    out = j.convert_experience([{"title": "A", "organization": "B", "timeline": "C"}])
    assert "resumeItemList" not in out


def test_summary_is_first_italic_bullet():
    out = j.convert_key_project([{"title": "P", "summary": "About", "bullets": ["x"]}])
    assert out.index(r"\textit{About}") < out.index(r"\resumeItem{x}")


def test_project_heading_format():
    out = j.convert_key_project([{"title": "Orbit", "organization": "DevCom", "timeline": "2026"}])
    assert r"\textbf{Orbit}\resumeSep\emph{DevCom}" in squash(out)


def test_education_lines():
    out = j.convert_education([{"examination": "Class XII", "institute": "School",
                                "university": "CBSE", "year": "2021", "cpi": "95%"}])
    s = squash(out)
    assert "{School,CBSE}{2021}" in s and r"{ClassXII}{CPI/Score:95\%}" in s
    same = j.convert_education([{"institute": "IIT", "university": "IIT", "examination": "B"}])
    assert squash(same).count("IIT") == 1


def test_skills_no_trailing_linebreak():
    out = j.convert_technical_skills([{"category": "Lang", "skills": ["Py", "C"]},
                                      {"category": "FW", "skills": ["Django"]}])
    assert out.count(r"\\") == 1
    assert not re.search(r"\\\\\s*\\resumeSkillsListEnd", out)


def test_header():
    out = j.convert_header({"name": "Asha Rao", "phone": "+91 99", "email": "a@x.com",
                            "degree": "B.Tech.", "department": "CSE", "gender": "F"})
    assert out.startswith(r"\resumeHeader{Asha Rao}")
    assert r"\href{mailto:a@x.com}{\underline{a@x.com}}" in out and "gender" not in out.lower()
    assert balanced(out)


def test_scholastic_year_optional():
    out = j.convert_scholastic_achievements(["AIR 1", {"text": "Rank 1", "year": "2022"}])
    assert r"\resumeAchievement{AIR 1}{}" in out and r"\resumeAchievement{Rank 1}{2022}" in out


def test_empty_and_invalid():
    assert j.convert_education([]) == "" and j.convert_courses([]) == ""
    for fn in (j.convert_experience, j.convert_key_project, j.convert_pors):
        try:
            fn([{"organization": "x"}])
            assert False
        except ValueError:
            pass


def test_pors_happy_path():
    out = j.convert_pors([
        {
            "role": "Coordinator",
            "organization": "Club",
            "duration": "2024",
            "bullets": ["Organized fest"],
            "summary": "Led team of 10",
        }
    ])
    assert r"\section{Positions of Responsibility}" in out
    assert r"\resumeSubheading" in out
    assert "{Coordinator}{2024}{Club}{}" in squash(out)
    assert r"\textit{Led team of 10}" in out
    assert r"\resumeItem{Organized fest}" in out
    assert balanced(out)


def test_courses_happy_path():
    out = j.convert_courses([
        {"category": "CS", "courses": ["DSA", "OS"], "note": "Grade A"},
        {"category": "Math", "courses": ["Calculus"]},
    ])
    assert r"\section{Courses Undertaken}" in out
    assert r"\resumeSkill{CS}{DSA, OS \textit{Grade A}}" in out
    assert r"\resumeSkill{Math}{Calculus}" in out
    assert out.count(r"\\") == 1
    assert balanced(out)


def test_input_type_validations():
    with pytest.raises(ValueError, match="Header must be a dictionary"):
        j.convert_header("invalid")

    with pytest.raises(ValueError, match="Missing key in header data: 'name'"):
        j.convert_header({"email": "test@test.com"})

    with pytest.raises(ValueError, match="Input must be a list of education entries"):
        j.convert_education("not-a-list")

    with pytest.raises(ValueError, match="Input must be a list of achievements"):
        j.convert_scholastic_achievements("not-a-list")

    with pytest.raises(ValueError, match="Each achievement must be a string or dict"):
        j.convert_scholastic_achievements([12345])

    with pytest.raises(ValueError, match="Input must be a list of skill categories"):
        j.convert_technical_skills("not-a-list")

    with pytest.raises(ValueError, match="'skills' must be a list"):
        j.convert_technical_skills([{"category": "Lang", "skills": "Python"}])
