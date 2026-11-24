"""Read-only refit proposals and selective, authenticated application."""

import base64
import hashlib
import json

from django.core import signing
from django.db import transaction

from resume_renderer.services.line_fitter import (
    _extract_bullets,
    _extract_project_summaries,
    _replace_bullet,
    fit_entries,
)
from resume_renderer.services.llm_client import GeminiLLMClient, LLMClientError
from resume_renderer.services.renderer import assemble_resume_latex, compile_latex
from resumes.models import Resume, SectionEntry
from resumes.serializers import SectionEntrySerializer

SALT = "resume-bullet-refit-v1"


def fingerprint(resume):
    sections = []
    for section in resume.sections.order_by("order", "id"):
        entries = list(
            section.entries.order_by("order", "id").values(
                "id",
                "order",
                "content",
                "content_origin",
                "raw_input",
                "generation_status",
            )
        )
        sections.append(
            [
                str(section.id),
                section.section_type_id,
                section.order,
                section.is_visible,
                entries,
            ]
        )
    data = [
        resume.template_id,
        resume.template.template_config,
        resume.visual_theme_id,
        resume.visual_theme.converter_set_key,
        resume.visual_theme.latex_preamble,
        resume.config_override,
        sections,
    ]
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, default=str).encode()
    ).hexdigest()


def preview_refit(resume, user, include_manual=False):
    before = fingerprint(resume)
    entries, excluded = {}, 0
    for section in resume.sections.filter(is_visible=True).select_related(
        "section_type"
    ):
        for entry in section.entries.filter(generation_status="done").order_by("order"):
            if not _extract_bullets(entry.content, section.section_type.key) and not _extract_project_summaries(entry.content, section.section_type.key):
                continue
            if entry.content_origin != "ai" and not include_manual:
                excluded += 1
                continue
            entries[str(entry.id)] = (section.section_type.key, entry.content)
    try:
        llm = GeminiLLMClient() if entries else None
    except LLMClientError:
        llm = None  # Measurements still work and the fitter reports unavailable revisions.
    fitted = fit_entries(resume, entries, llm)
    proposals, reports, errors = [], [], []
    for eid, result in fitted.items():
        failure = result["fitting"].get("error")
        if failure and failure not in errors:
            errors.append(failure)
        for report in result["fitting"]["bullets"] + result["fitting"].get("summaries", []):
            item = {**report, "entry_id": eid, "section_key": entries[eid][0]}
            reports.append(item)
            if report.get("proposed_bullets", [report["text"]]) != [report["original"]]:
                proposals.append({**item, "id": str(len(proposals))})
    # A concurrent edit during slow model calls must not produce an applicable preview.
    resume.refresh_from_db()
    if before != fingerprint(resume):
        raise ValueError("Resume changed while preparing proposals. Preview again.")
    token = signing.dumps(
        {
            "resume": str(resume.id),
            "user": str(user.pk),
            "snapshot": before,
            "include_manual": include_manual,
            "proposals": proposals,
        },
        salt=SALT,
        compress=True,
    )
    return {
        "token": token,
        "proposals": proposals,
        "reports": reports,
        "excluded_entries": excluded,
        "errors": errors,
    }


def apply_refit(resume, user, token, selected_ids):
    payload = signing.loads(token, salt=SALT, max_age=900)
    if payload.get("resume") != str(resume.id) or payload.get("user") != str(user.pk):
        raise signing.BadSignature("Proposal belongs to another resume or user.")
    proposals = {p["id"]: p for p in payload["proposals"]}
    if not set(selected_ids).issubset(proposals):
        raise ValueError("Selection contains an unknown proposal.")
    with transaction.atomic():
        locked = (
            Resume.objects.select_for_update()
            .select_related("template", "visual_theme")
            .get(pk=resume.pk)
        )
        entries = {
            str(e.id): e
            for e in SectionEntry.objects.select_for_update().filter(
                section__resume=locked
            )
        }
        if fingerprint(locked) != payload["snapshot"]:
            raise ValueError(
                "Resume content or layout changed. Preview again before applying."
            )
        changed = set()
        accepted_reports = {}
        # Replacements are indexed against the preview's original content.
        # Work from the last bullet backwards so splits cannot shift later paths.
        ordered_ids = sorted(
            set(selected_ids),
            key=lambda pid: (
                proposals[pid]["entry_id"],
                proposals[pid]["path"][0],
                str(proposals[pid]["path"][1]),
                proposals[pid]["path"][2],
            ),
            reverse=True,
        )
        for pid in ordered_ids:
            proposal = proposals[pid]
            entry = entries[proposal["entry_id"]]
            if entry.content_origin != "ai" and not payload["include_manual"]:
                raise ValueError("Manual content was not included in this preview.")
            if proposal.get("kind") == "summary":
                entry.content[proposal["path"][0]]["summary"] = proposal["text"]
            else:
                _replace_bullet(
                    entry.content,
                    proposal["path"],
                    proposal.get("proposed_bullets", [proposal["text"]]),
                )
            # Preserve origin: one accepted refit never removes manual-edit protection.
            accepted_reports.setdefault(str(entry.id), []).append(
                {
                    k: v
                    for k, v in proposal.items()
                    if k not in {"id", "entry_id", "section_key"}
                }
            )
            changed.add(str(entry.id))
        for eid in changed:
            reports = accepted_reports[eid]
            entries[eid].fitting = {
                "status": "partial"
                if any(r["status"] == "unfitted" for r in reports)
                else "complete",
                "bullets": [r for r in reports if r.get("kind") != "summary"],
                "summaries": [r for r in reports if r.get("kind") == "summary"],
            }
            entries[eid].save(update_fields=["content", "fitting", "updated_at"])
        if not changed:
            return {"entries": []}
        locked.latex_cache_valid = False
        locked.save(update_fields=["latex_cache_valid", "updated_at"])
        latex = assemble_resume_latex(locked)
        pdf = compile_latex(latex)
    return {
        "entries": SectionEntrySerializer(
            [entries[eid] for eid in changed], many=True
        ).data,
        "pdf": base64.b64encode(pdf).decode(),
        "latex": latex,
    }
