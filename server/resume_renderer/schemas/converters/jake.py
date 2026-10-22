r"""
Jake's resume converters (pdflatex, sb2nov-based look).

Emit ONLY macros defined in the jake-classic visual-theme preamble:
\resumeHeader, \resumeSep, \section,
\resumeSubHeadingListStart/End, \resumeSubheading, \resumeProjectHeading,
\resumeItemListStart/End, \resumeItem,
\resumeSkillsListStart/End, \resumeSkill,
\resumeAchievementListStart/End, \resumeAchievement

Signature is (data, config=None) so assemble_resume_latex can pass
config_override without hitting its TypeError fallback.
"""

import re

from ...services.json_sanitizer import sanitize_text
from ...services.markdown_parser import MARKDOWN_PARSER

_SEP = r" \resumeSep "     # spaces matter: "\resumeSepX" would be one control word
_EMAIL_RE = re.compile(r"^[\w.+\-]+@[\w\-]+(\.[\w\-]+)+$")


# --------------------------------------------------------------------------
# Shared helpers (all text goes through _t / _plain: single choke point)
# --------------------------------------------------------------------------
def _t(value) -> str:
    """sanitize + markdown. None -> ''."""
    if value is None:
        return ""
    return MARKDOWN_PARSER.parse(sanitize_text(str(value).strip()))


def _plain(value) -> str:
    """sanitize only (emails, phones: no markdown)."""
    if value is None:
        return ""
    return sanitize_text(str(value).strip())


def _as_list(value, name: str) -> list:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"'{name}' must be a list.")
    return value


def _item_list(bullets: list, summary=None) -> str:
    r"""Nested bullet list (level 2, so \labelitemii small dots apply).
    Returns '' when empty: an empty itemize is a LaTeX error.
    summary becomes the first bullet, in italics."""
    items = []
    s = _t(summary)
    if s:
        items.append(rf"\textit{{{s}}}")
    items.extend(b for b in (_t(x) for x in bullets) if b)
    if not items:
        return ""
    body = "\n".join(rf"        \resumeItem{{{i}}}" for i in items)
    return f"      \\resumeItemListStart\n{body}\n      \\resumeItemListEnd"


def _subheading(left1: str, right1: str, left2: str, right2: str, items: str = "") -> str:
    head = (
        "    \\resumeSubheading\n"
        f"      {{{left1}}}{{{right1}}}\n"
        f"      {{{left2}}}{{{right2}}}"
    )
    return head + ("\n" + items if items else "")


def _project_heading(title: str, org: str, date: str, items: str = "") -> str:
    left = rf"\textbf{{{title}}}" + (rf"{_SEP}\emph{{{org}}}" if org else "")
    head = "    \\resumeProjectHeading\n" + f"      {{{left}}}{{{date}}}"
    return head + ("\n" + items if items else "")


def _section(title: str, rows: list) -> str:
    return "\n".join(
        [
            rf"\section{{{title}}}",
            r"\resumeSubHeadingListStart",
            *rows,
            r"\resumeSubHeadingListEnd",
        ]
    )


def _entries(section_title: str, data, label: str, build) -> str:
    if not isinstance(data, list):
        raise ValueError(f"Input must be a list of {label} entries.")
    rows = []
    for item in data:
        if not isinstance(item, dict):
            raise ValueError(f"Each {label} entry must be a dictionary.")
        row = build(item)
        if row:
            rows.append(row)
    return _section(section_title, rows) if rows else ""


def _skill_rows(data, label: str, list_key: str) -> list:
    if not isinstance(data, list):
        raise ValueError(f"Input must be a list of {label} categories.")
    rows = []
    for item in data:
        if not isinstance(item, dict):
            raise ValueError(f"Each {label} entry must be a dictionary.")
        category = _t(item.get("category"))
        values = _as_list(item.get(list_key), list_key)
        joined = ", ".join(_t(v) for v in values if isinstance(v, str) and v.strip())
        note = _t(item.get("note"))
        if note:
            joined = f"{joined} \\textit{{{note}}}".strip()
        if category or joined:
            rows.append(rf"  \resumeSkill{{{category}}}{{{joined}}}")
    return rows


def _skills_section(title: str, rows: list) -> str:
    # rows joined with " \\", NO trailing "\\" (it would add a blank line)
    return (
        rf"\section{{{title}}}" "\n"
        r"\resumeSkillsListStart" "\n"
        + " \\\\\n".join(rows)
        + "\n"
        r"\resumeSkillsListEnd"
    )


# --------------------------------------------------------------------------
# Section converters
# --------------------------------------------------------------------------
def convert_header(header: dict, config=None) -> str:
    if not isinstance(header, dict):
        raise ValueError("Header must be a dictionary.")

    name = _t(header.get("name"))
    if not name:
        raise ValueError("Missing key in header data: 'name'")

    extra = _SEP.join(
        p
        for p in (
            _t(header.get("degree")),
            _t(header.get("department")),
            _t(header.get("institution")),
            _t(header.get("roll_no")),
        )
        if p
    )

    contact = []
    phone = _plain(header.get("phone"))
    if phone:
        contact.append(phone)
    email_raw = str(header.get("email") or "").strip()
    if email_raw:
        shown = _plain(email_raw)
        # link target uses the raw (regex-validated) address, display text is escaped
        contact.append(
            rf"\href{{mailto:{email_raw}}}{{\underline{{{shown}}}}}"
            if _EMAIL_RE.match(email_raw)
            else shown
        )

    return rf"\resumeHeader{{{name}}}{{{extra}}}{{{_SEP.join(contact)}}}"


def convert_education(education: list, config=None) -> str:
    def build(edu: dict) -> str:
        exam = _t(edu.get("examination"))
        inst = _t(edu.get("institute"))
        univ = _t(edu.get("university"))
        year = _t(edu.get("year"))
        if not (exam or inst or univ):
            return ""
        line1 = f"{inst}, {univ}" if (inst and univ and inst != univ) else (inst or univ)
        cpi = str(edu.get("cpi") or "").strip()
        score = _t(f"CPI/Score: {cpi}") if cpi else ""
        note = str(edu.get("note") or "").strip()
        return _subheading(line1, year, exam, score, _item_list([note] if note else []))

    return _entries("Education", education, "education", build)


def convert_experience(experiences: list, config=None) -> str:
    def build(e: dict) -> str:
        title = _t(e.get("title"))
        if not title:
            raise ValueError("Missing key in experience data: 'title'")
        return _subheading(
            title,
            _t(e.get("timeline")),
            _t(e.get("organization")),
            _t(e.get("location")),
            _item_list(_as_list(e.get("bullets"), "bullets"), e.get("summary")),
        )

    return _entries("Experience", experiences, "experience", build)


def convert_key_project(projects: list, config=None) -> str:
    def build(p: dict) -> str:
        title = _t(p.get("title"))
        if not title:
            raise ValueError("Missing key in project data: 'title'")
        return _project_heading(
            title,
            _t(p.get("organization")),
            _t(p.get("timeline")),
            _item_list(_as_list(p.get("bullets"), "bullets"), p.get("summary")),
        )

    return _entries("Projects", projects, "project", build)


def convert_pors(positions: list, config=None) -> str:
    def build(p: dict) -> str:
        role = _t(p.get("role"))
        if not role:
            raise ValueError("Missing key in position data: 'role'")
        return _subheading(
            role,
            _t(p.get("duration")),
            _t(p.get("organization")),
            "",
            _item_list(_as_list(p.get("bullets"), "bullets"), p.get("summary")),
        )

    return _entries("Positions of Responsibility", positions, "position", build)


def convert_scholastic_achievements(achievements: list, config=None) -> str:
    if not isinstance(achievements, list):
        raise ValueError("Input must be a list of achievements.")
    rows = []
    for ach in achievements:
        if isinstance(ach, str):
            text, year = _t(ach), ""
        elif isinstance(ach, dict):
            text, year = _t(ach.get("text")), _t(ach.get("year"))
        else:
            raise ValueError(f"Each achievement must be a string or dict, got: {type(ach)}")
        if text:
            rows.append(rf"  \resumeAchievement{{{text}}}{{{year}}}")
    if not rows:
        return ""
    return "\n".join(
        [
            r"\section{Scholastic Achievements}",
            r"\resumeAchievementListStart",
            *rows,
            r"\resumeAchievementListEnd",
        ]
    )


def convert_courses(courses_data: list, config=None) -> str:
    rows = _skill_rows(courses_data, "course", "courses")
    return _skills_section("Courses Undertaken", rows) if rows else ""


def convert_technical_skills(skills_data: list, config=None) -> str:
    rows = _skill_rows(skills_data, "skill", "skills")
    return _skills_section("Technical Skills", rows) if rows else ""
