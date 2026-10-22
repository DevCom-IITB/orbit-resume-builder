import base64
import copy
from dataclasses import dataclass
from typing import Any, List

from resumes.models import Resume, ResumeTemplate, Section, SectionEntry, TemplateSectionType, VisualTheme
from resume_renderer.services.renderer import assemble_resume_latex, compile_latex
from resume_renderer.services.styling import (
    _validate_contrast,
    _validate_hex,
    get_style_options,
    resolve_style,
)


def section_has_content(section: Section) -> bool:
    """Return True if section has at least one entry with non-empty content."""
    for entry in section.entries.all():
        if entry.content is not None and entry.content != "" and entry.content != {} and entry.content != []:
            return True
    return False


@dataclass
class SectionUpdateAction:
    section: Section
    new_order: int
    new_is_visible: bool


@dataclass
class SectionCreateAction:
    template_section_type: TemplateSectionType
    new_order: int
    new_is_visible: bool


@dataclass
class SwitchPlan:
    is_noop: bool
    template: ResumeTemplate
    theme: VisualTheme
    will_hide: List[str]
    will_add_empty: List[str]
    will_restore: List[str]
    style_reset: List[str]
    unchanged: List[str]
    section_updates: List[SectionUpdateAction]
    section_creates: List[SectionCreateAction]
    duplicate_sections_to_hide: List[Section]
    updated_hidden_by_switch: List[str]
    updated_style: dict
    warnings: List[str]


def plan_switch(resume: Resume, template: ResumeTemplate, theme: VisualTheme) -> SwitchPlan:
    """
    Pure planning function: compute the exact differences and actions required
    to switch *resume* to *template* with *theme*. Performs NO database writes.
    """
    current_template = getattr(resume, "template", None)
    if current_template is None:
        try:
            current_template = ResumeTemplate.objects.get(key="iitb-general")
        except ResumeTemplate.DoesNotExist:
            current_template = None

    current_theme = getattr(resume, "visual_theme", None)
    is_noop = (
        current_template is not None
        and current_template.pk == template.pk
        and current_theme is not None
        and current_theme.pk == theme.pk
    )

    manifest_tsts = list(
        TemplateSectionType.objects.filter(template=template)
        .select_related("section_type")
        .order_by("default_order")
    )
    manifest_by_key = {tst.section_type.key: tst for tst in manifest_tsts}

    raw_sections = list(
        resume.sections.select_related("section_type")
        .prefetch_related("entries")
        .order_by("order")
    )

    seen_keys = set()
    unique_sections: List[Section] = []
    duplicate_sections_to_hide: List[Section] = []
    for s in raw_sections:
        k = s.section_type.key
        if k in seen_keys:
            duplicate_sections_to_hide.append(s)
        else:
            seen_keys.add(k)
            unique_sections.append(s)

    current_sections_by_key = {s.section_type.key: s for s in unique_sections}

    config = resume.config_override or {}
    switch_cfg = config.get("template_switch") or {}
    stored_hidden_by_switch = list(switch_cfg.get("hidden_by_switch") or [])

    will_restore: List[str] = []
    remaining_hidden_by_switch: List[str] = []

    for key in stored_hidden_by_switch:
        sec = current_sections_by_key.get(key)
        if not sec:
            continue
        if sec.is_visible:
            continue
        if key in manifest_by_key:
            will_restore.append(key)
        else:
            remaining_hidden_by_switch.append(key)

    will_hide: List[str] = []
    newly_hidden_by_switch: List[str] = []

    for sec in unique_sections:
        sec_key = sec.section_type.key
        if sec_key not in manifest_by_key:
            if sec.is_visible:
                newly_hidden_by_switch.append(sec_key)
                if section_has_content(sec):
                    will_hide.append(sec_key)

    updated_hidden_by_switch = list(remaining_hidden_by_switch)
    for k in newly_hidden_by_switch:
        if k not in updated_hidden_by_switch:
            updated_hidden_by_switch.append(k)

    will_add_empty: List[str] = []
    missing_tsts: List[TemplateSectionType] = []

    for tst in manifest_tsts:
        k = tst.section_type.key
        if k not in current_sections_by_key:
            will_add_empty.append(k)
            missing_tsts.append(tst)

    unchanged: List[str] = []
    for sec in unique_sections:
        k = sec.section_type.key
        if k in manifest_by_key and k not in will_restore:
            unchanged.append(k)

    # Remap section ordering: preserve relative order of existing sections,
    # and insert missing sections at nearest preceding manifest position.
    ordered_items: List[Any] = list(unique_sections)
    present_keys = set(current_sections_by_key.keys())

    for missing_tst in missing_tsts:
        preceding_keys = [
            t.section_type.key for t in manifest_tsts if t.default_order < missing_tst.default_order
        ]
        cands = [k for k in preceding_keys if k in present_keys]
        if cands:
            nearest_key = cands[-1]
            nearest_idx = -1
            for idx, item in enumerate(ordered_items):
                if getattr(item.section_type, "key", None) == nearest_key:
                    nearest_idx = idx
                    break

            insert_idx = nearest_idx + 1
            while insert_idx < len(ordered_items) and isinstance(ordered_items[insert_idx], TemplateSectionType):
                if ordered_items[insert_idx].default_order < missing_tst.default_order:
                    insert_idx += 1
                else:
                    break
            ordered_items.insert(insert_idx, missing_tst)
        else:
            insert_idx = 0
            while insert_idx < len(ordered_items) and isinstance(ordered_items[insert_idx], TemplateSectionType):
                if ordered_items[insert_idx].default_order < missing_tst.default_order:
                    insert_idx += 1
                else:
                    break
            ordered_items.insert(insert_idx, missing_tst)

    section_updates: List[SectionUpdateAction] = []
    section_creates: List[SectionCreateAction] = []

    for idx, item in enumerate(ordered_items):
        if isinstance(item, Section):
            sec_key = item.section_type.key
            if sec_key not in manifest_by_key:
                new_visible = False
            elif sec_key in will_restore:
                new_visible = True
            elif manifest_by_key[sec_key].is_required:
                new_visible = True
            else:
                new_visible = item.is_visible
            section_updates.append(
                SectionUpdateAction(section=item, new_order=idx, new_is_visible=new_visible)
            )
        elif isinstance(item, TemplateSectionType):
            new_visible = bool(item.is_default or item.is_required)
            section_creates.append(
                SectionCreateAction(template_section_type=item, new_order=idx, new_is_visible=new_visible)
            )

    # Style checks: Reset font and accent to target template's authentic original defaults
    style_reset: List[str] = []
    stored_style = dict((config.get("style") or {}))
    updated_style = dict(stored_style)

    opts = get_style_options(template)
    target_font_default = opts["font_default"]
    target_accent_default = opts["accent_default"].upper()

    if not is_noop:
        current_style = resolve_style(resume)
        if current_style.get("font") != target_font_default:
            style_reset.append("font")
        if current_style.get("accent", "").upper() != target_accent_default:
            style_reset.append("accent")

        # Clear font and accent overrides so resume adopts the new template's authentic defaults
        updated_style.pop("font", None)
        updated_style.pop("accent", None)

    # Line and word spacing: keep if valid in new template options, else drop and reset
    valid_line_options = opts.get("line_spacings", [])
    valid_word_options = opts.get("word_spacings", [])

    if "line_spacing" in stored_style:
        stored_line = str(stored_style["line_spacing"])
        if stored_line not in valid_line_options:
            style_reset.append("line_spacing")
            updated_style.pop("line_spacing", None)
        else:
            updated_style["line_spacing"] = stored_line

    if "word_spacing" in stored_style:
        stored_word = str(stored_style["word_spacing"])
        if stored_word not in valid_word_options:
            style_reset.append("word_spacing")
            updated_style.pop("word_spacing", None)
        else:
            updated_style["word_spacing"] = stored_word

    warnings: List[str] = []
    for k in will_hide:
        sec = current_sections_by_key[k]
        warnings.append(
            f"Section '{sec.section_type.display_name}' has content but is hidden in template '{template.display_name}'."
        )

    return SwitchPlan(
        is_noop=is_noop,
        template=template,
        theme=theme,
        will_hide=will_hide,
        will_add_empty=will_add_empty,
        will_restore=will_restore,
        style_reset=style_reset,
        unchanged=unchanged,
        section_updates=section_updates,
        section_creates=section_creates,
        duplicate_sections_to_hide=duplicate_sections_to_hide,
        updated_hidden_by_switch=updated_hidden_by_switch,
        updated_style=updated_style,
        warnings=warnings,
    )


def apply_switch(resume: Resume, plan: SwitchPlan) -> dict:
    """
    Apply *plan* to *resume* in an atomic database transaction.
    Renders LaTeX and compiles PDF inside the transaction so any failure triggers full rollback.
    """
    from django.db import transaction

    with transaction.atomic():
        locked = Resume.objects.select_for_update().get(pk=resume.pk)

        # 1. Update existing sections
        for action in plan.section_updates:
            Section.objects.filter(pk=action.section.pk).update(
                order=action.new_order,
                is_visible=action.new_is_visible,
            )

        # 2. Hide duplicates if any existed
        for dup in plan.duplicate_sections_to_hide:
            Section.objects.filter(pk=dup.pk).update(is_visible=False)

        # 3. Create missing sections
        for create_action in plan.section_creates:
            tst = create_action.template_section_type
            new_sec = Section.objects.create(
                resume=locked,
                section_type=tst.section_type,
                order=create_action.new_order,
                is_visible=create_action.new_is_visible,
            )
            if not tst.section_type.allow_multiple_entries:
                SectionEntry.objects.create(
                    section=new_sec,
                    order=0,
                    raw_input="",
                    content=None,
                    generation_status="pending",
                )

        # 4. Update Resume fields & config_override (new dict assignment)
        new_config = copy.deepcopy(locked.config_override or {})
        if plan.updated_style:
            new_config["style"] = plan.updated_style
        elif "style" in new_config:
            new_config.pop("style", None)

        ts_cfg = dict(new_config.get("template_switch") or {})
        ts_cfg["hidden_by_switch"] = plan.updated_hidden_by_switch
        new_config["template_switch"] = ts_cfg

        locked.template = plan.template
        locked.visual_theme = plan.theme
        locked.config_override = new_config
        locked.latex_cache_valid = False
        locked.cached_latex = None
        locked.save(
            update_fields=[
                "template",
                "visual_theme",
                "config_override",
                "latex_cache_valid",
                "cached_latex",
                "updated_at",
            ]
        )

        # 5. Assemble LaTeX and compile INSIDE the same atomic block
        latex = assemble_resume_latex(locked)
        pdf_bytes = compile_latex(latex)

    # After atomic block commits:
    resume.refresh_from_db()
    pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")

    sections_data = [
        {
            "key": s.section_type.key,
            "display_name": s.section_type.display_name,
            "order": s.order,
            "is_visible": s.is_visible,
            "has_data": section_has_content(s),
        }
        for s in resume.sections.select_related("section_type").prefetch_related("entries").order_by("order")
    ]

    res_data = {
        "changed": True,
        "template": {
            "key": plan.template.key,
            "display_name": plan.template.display_name,
        },
        "theme_key": plan.theme.key,
        "sections": sections_data,
        "style": resolve_style(resume),
        "options": get_style_options(plan.template),
        "warnings": plan.warnings,
        "pdf": pdf_b64,
        "latex": latex,
    }

    try:
        import fitz
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        res_data["pages"] = doc.page_count
        res_data["page_count"] = doc.page_count
    except Exception:
        pass

    return res_data
