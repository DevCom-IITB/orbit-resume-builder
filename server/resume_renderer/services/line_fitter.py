"""
Bullet line-fitting post-processor.

After LLM generation, measures each bullet's rendered width using the actual
LaTeX font (via the persistent latex-renderer Docker container) and issues one
targeted repair call for any bullet outside the target band.

Column geometry (from the template in renderer.py):
  A4 width 595.276pt − left 40.12pt − right 40.12pt = textwidth 515.04pt
  itemize leftmargin 15pt → bullet text column ≈ 500pt
"""
import copy
import json
import re
import tarfile
import uuid
from io import BytesIO

BULLET_LINE_WIDTH_PT = 500.0
TARGET_LOW_RATIO = 0.88  # below this → too short, wasted whitespace
AVG_CHAR_PT = 5.26       # cmr10 10pt average character width in pt

# Fields that contain bullet lists, keyed by section type
_BULLET_FIELD_MAP: dict[str, tuple[str, ...]] = {
    "professional_experience": ("bullets",),
    "key_projects": ("bullets",),
    "positions_of_responsibility": ("bullets",),
}

_LATEX_ESCAPE = str.maketrans({
    "\\": r"\textbackslash{}",
    "{":  r"\{",
    "}":  r"\}",
    "$":  r"\$",
    "&":  r"\&",
    "#":  r"\#",
    "^":  r"\^{}",
    "_":  r"\_",
    "~":  r"\~{}",
    "%":  r"\%",
})

_MEASURE_DOC = (
    r"\documentclass[10pt]{article}" "\n"
    r"\usepackage[T1]{fontenc}" "\n"
    r"\newlength{\bwx}" "\n"
    r"\begin{document}" "\n"
    "__ITEMS__"
    r"\end{document}" "\n"
)


def _escape_latex(text: str) -> str:
    return text.translate(_LATEX_ESCAPE)


def _build_measure_doc(texts: list[str]) -> str:
    lines = []
    for t in texts:
        safe = _escape_latex(t)
        lines.append(rf"\settowidth{{\bwx}}{{{safe}}}\typeout{{W:\the\bwx}}")
    return _MEASURE_DOC.replace("__ITEMS__", "\n".join(lines) + "\n")


def _measure_via_container(texts: list[str]) -> list[float]:
    """
    Returns rendered widths in pt for each text string using the running
    latex-renderer container. Returns -1.0 for each on any error.
    """
    if not texts:
        return []

    from resume_renderer.services.renderer import _get_latex_container

    try:
        container = _get_latex_container()
    except Exception:
        return [-1.0] * len(texts)

    latex_src = _build_measure_doc(texts).encode("utf-8")
    tar_buf = BytesIO()
    with tarfile.open(fileobj=tar_buf, mode="w") as tar:
        info = tarfile.TarInfo(name="measure.tex")
        info.size = len(latex_src)
        tar.addfile(tarinfo=info, fileobj=BytesIO(latex_src))
    tar_buf.seek(0)

    # Each measurement gets its own directory: the container is shared by all
    # requests, so a fixed path let concurrent jobs overwrite each other.
    workdir = f"/usr/src/tex/measure-{uuid.uuid4().hex}"
    try:
        container.exec_run(cmd=["mkdir", "-p", workdir])
        container.put_archive(workdir, tar_buf.read())
        _, out = container.exec_run(
            cmd="pdflatex -interaction=nonstopmode measure.tex",
            workdir=workdir,
        )
        log = out.decode("utf-8", errors="replace")
    except Exception:
        return [-1.0] * len(texts)
    finally:
        try:
            container.exec_run(cmd=["rm", "-rf", workdir])
        except Exception:
            pass

    widths: list[float] = [float(m.group(1)) for m in re.finditer(r"W:([\d.]+)pt", log)]
    while len(widths) < len(texts):
        widths.append(-1.0)
    return widths[:len(texts)]


def _extract_bullets(content, section_key: str) -> list[tuple]:
    """
    Returns a flat list of (entry_idx, field, bullet_idx, text).
    For scholastic_achievements: entry_idx=0, field=None, bullet_idx=array idx.
    """
    refs: list[tuple] = []
    if section_key == "scholastic_achievements":
        if isinstance(content, list):
            for i, text in enumerate(content):
                if isinstance(text, str):
                    refs.append((0, None, i, text))
        return refs

    fields = _BULLET_FIELD_MAP.get(section_key)
    if not fields or not isinstance(content, list):
        return refs
    for ei, entry in enumerate(content):
        if not isinstance(entry, dict):
            continue
        for field in fields:
            for bi, text in enumerate(entry.get(field) or []):
                if isinstance(text, str):
                    refs.append((ei, field, bi, text))
    return refs


def _apply_fixes(content, section_key: str, fix_map: dict[int, str], refs: list[tuple]):
    content = copy.deepcopy(content)
    for flat_idx, new_text in fix_map.items():
        if not isinstance(new_text, str) or flat_idx >= len(refs):
            continue
        ei, field, bi, _ = refs[flat_idx]
        if section_key == "scholastic_achievements":
            content[bi] = new_text
        else:
            content[ei][field][bi] = new_text
    return content


def _build_repair_prompt(bad: list[tuple]) -> str:
    """bad: list of (flat_idx, text, width_pt, ratio)"""
    line_width = BULLET_LINE_WIDTH_PT
    items = []
    for flat_idx, text, width_pt, ratio in bad:
        delta_pt = abs(width_pt - line_width)
        delta_chars = max(1, round(delta_pt / AVG_CHAR_PT))
        if ratio > 1.0:
            issue = f"TOO LONG — shorten by ~{delta_chars} chars (do not cut facts)"
        else:
            issue = (
                f"TOO SHORT — add ~{delta_chars} chars of detail "
                f"(method/tool/metric implied by context; invent nothing specific)"
            )
        items.append(
            f'  {{"index": {flat_idx}, "text": {json.dumps(text)}, "issue": "{issue}"}}'
        )

    return (
        f"You are editing resume bullet points to fit one printed line.\n\n"
        f"The LaTeX text column is {line_width:.0f}pt wide. "
        f"Each bullet must render between {line_width * TARGET_LOW_RATIO:.0f}pt and {line_width:.0f}pt.\n\n"
        "Fix ONLY the bullets listed. Return ONLY valid JSON, no markdown:\n"
        '{\"fixes\": [{\"index\": <number>, \"bullet\": \"<fixed text>\"}]}\n\n'
        "Bullets to fix:\n[\n"
        + ",\n".join(items)
        + "\n]"
    )


def fit_bullets_in_content(content, section_key: str, llm_client):
    """
    Measure bullet widths and repair out-of-band ones with one LLM retry.
    Returns (possibly modified) content. Never raises — degrades silently.
    """
    refs = _extract_bullets(content, section_key)
    if not refs:
        return content

    texts = [r[3] for r in refs]
    widths = _measure_via_container(texts)

    bad: list[tuple] = []
    for i, ref in enumerate(refs):
        w = widths[i]
        if w <= 0:
            continue
        ratio = w / BULLET_LINE_WIDTH_PT
        if ratio < TARGET_LOW_RATIO or ratio > 1.0:
            bad.append((i, ref[3], w, ratio))

    if not bad:
        return content

    try:
        repair_result = llm_client.generate_json(_build_repair_prompt(bad))
    except Exception:
        return content

    if not isinstance(repair_result, dict):
        return content

    fix_map: dict[int, str] = {}
    for fix in repair_result.get("fixes", []):
        if isinstance(fix, dict) and "index" in fix and "bullet" in fix:
            idx = fix["index"]
            if isinstance(idx, int):
                fix_map[idx] = fix["bullet"]

    return _apply_fixes(content, section_key, fix_map, refs) if fix_map else content
