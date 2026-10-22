"""
Awesome-CV style converters (pdflatex port).

Emit ONLY macros defined in the awesome-cv visual-theme preamble:
\\cvheader, \\cvsection, cventries/\\cventry, cvitems, \\cvsummary,
cvhonors/\\cvhonor, cvskills/\\cvskill, \\cvsep

Signature is (data, config=None) so assemble_resume_latex can pass
config_override without hitting its TypeError fallback.
"""

import re

from ...services.json_sanitizer import sanitize_text
from ...services.markdown_parser import MARKDOWN_PARSER

_DOT = r"\enskip$\cdot$\enskip"   # \cdotp is math-only, do not use in text
_SEP = r" \cvsep "
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


def _items(bullets: list, summary=None) -> str:
    """cvitems block. Returns '' when there is nothing to list
    (an empty itemize is a LaTeX error)."""
    parts = []
    s = _t(summary)
    if s:
        parts.append(rf"    \cvsummary{{{s}}}")
    clean = [b for b in (_t(x) for x in bullets) if b]
    if clean:
        parts.append(r"    \begin{cvitems}")
        # braces after \item: a bullet starting with '[' would be eaten as optional arg
        parts.extend(rf"      \item {{{b}}}" for b in clean)
        parts.append(r"    \end{cvitems}")
    return "\n".join(parts)


def _entry(title: str, org: str = "", loc: str = "", date: str = "", body: str = "") -> str:
    body_arg = f"{{\n{body}\n  }}" if body else "{}"
    return rf"""\cventry
  {{{title}}}
  {{{org}}}
  {{{loc}}}
  {{{date}}}
  {body_arg}"""


def _wrap(section_title: str, env: str, rows: list, sep: str = "\n\n") -> str:
    return (
        rf"\cvsection{{{section_title}}}" "\n"
        rf"\begin{{{env}}}" "\n"
        + sep.join(rows)
        + "\n"
        rf"\end{{{env}}}"
    )


def _entries_section(section_title, data, label, title_key, org_key, date_key, loc_key=None) -> str:
    """Shared by experience / projects / PoR."""
    if not isinstance(data, list):
        raise ValueError(f"Input must be a list of {label} entries.")
    entries = []
    for item in data:
        if not isinstance(item, dict):
            raise ValueError(f"Each {label} entry must be a dictionary.")
        title = _t(item.get(title_key))
        if not title:
            raise ValueError(f"Missing key in {label} data: '{title_key}'")
        body = _items(_as_list(item.get("bullets"), "bullets"), item.get("summary"))
        entries.append(
            _entry(
                title,
                _t(item.get(org_key)),
                _t(item.get(loc_key)) if loc_key else "",
                _t(item.get(date_key)),
                body,
            )
        )
    return _wrap(section_title, "cventries", entries) if entries else ""


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
            rows.append(rf"  \cvskill{{{category}}}{{{joined}}}")
    return rows


# --------------------------------------------------------------------------
# Section converters
# --------------------------------------------------------------------------
def convert_header(header: dict, config=None) -> str:
    if not isinstance(header, dict):
        raise ValueError("Header must be a dictionary.")

    name = str(header.get("name") or "").strip()
    if not name:
        raise ValueError("Missing key in header data: 'name'")
    words = name.split()
    first, last = (" ".join(words[:-1]), words[-1]) if len(words) > 1 else (name, "")

    position = f" {_DOT} ".join(
        p for p in (_t(header.get("degree")), _t(header.get("department"))) if p
    )
    extra = _SEP.join(
        p for p in (_t(header.get("roll_no")), _t(header.get("institution"))) if p
    )

    contact = []
    email_raw = str(header.get("email") or "").strip()
    if email_raw:
        shown = _plain(email_raw)
        # link target uses the raw address (validated), display text is escaped
        contact.append(
            rf"\href{{mailto:{email_raw}}}{{{shown}}}" if _EMAIL_RE.match(email_raw) else shown
        )
    phone = _plain(header.get("phone"))
    if phone:
        contact.append(phone)
    contact_line = _SEP.join(contact)

    return rf"\cvheader{{{_t(first)}}}{{{_t(last)}}}{{{position}}}{{{extra}}}{{{contact_line}}}"


def convert_education(education: list, config=None) -> str:
    if not isinstance(education, list):
        raise ValueError("Input must be a list of education entries.")
    entries = []
    for edu in education:
        if not isinstance(edu, dict):
            raise ValueError("Each education entry must be a dictionary.")
        exam = _t(edu.get("examination"))
        inst = _t(edu.get("institute"))
        univ = _t(edu.get("university"))
        year = _t(edu.get("year"))
        if not (exam or inst or univ):
            continue
        if not inst:                       # only university given -> use it as org line
            inst, univ = univ, ""
        raw_bullets = []
        cpi = str(edu.get("cpi") or "").strip()
        if cpi:
            raw_bullets.append(f"CPI/Score: {cpi}")
        note = str(edu.get("note") or "").strip()
        if note:
            raw_bullets.append(note)
        entries.append(_entry(exam, inst, univ, year, _items(raw_bullets)))
    return _wrap("Education", "cventries", entries) if entries else ""


def convert_experience(experiences: list, config=None) -> str:
    return _entries_section(
        "Professional Experience", experiences, "experience",
        title_key="title", org_key="organization", date_key="timeline", loc_key="location",
    )


def convert_key_project(projects: list, config=None) -> str:
    return _entries_section(
        "Key Projects", projects, "project",
        title_key="title", org_key="organization", date_key="timeline",
    )


def convert_pors(positions: list, config=None) -> str:
    return _entries_section(
        "Positions of Responsibility", positions, "position",
        title_key="role", org_key="organization", date_key="duration",
    )


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
            # award arg empty -> text stays regular weight
            rows.append(rf"  \cvhonor{{}}{{{text}}}{{}}{{{year}}}")
    return _wrap("Scholastic Achievements", "cvhonors", rows, sep="\n") if rows else ""


def convert_courses(courses_data: list, config=None) -> str:
    rows = _skill_rows(courses_data, "course", "courses")
    return _wrap("Courses Undertaken", "cvskills", rows, sep="\n") if rows else ""


def convert_technical_skills(skills_data: list, config=None) -> str:
    rows = _skill_rows(skills_data, "skill", "skills")
    return _wrap("Technical Skills", "cvskills", rows, sep="\n") if rows else ""
