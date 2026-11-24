import copy
from unittest.mock import Mock

import pytest
from django.core import signing
from django.core.management import call_command
from rest_framework.test import APIClient

from resumes.models import (
    Resume,
    ResumeTemplate,
    Section,
    SectionEntry,
    SectionTypeDefinition,
)
from resumes.services import refit
from resume_renderer.services.prompts import get_candidate_schema

pytestmark = pytest.mark.django_db


@pytest.fixture
def sample(django_user_model):
    call_command("seed_templates")
    user = django_user_model.objects.create_user(username="fituser")
    template = ResumeTemplate.objects.get(key="jake-general")
    resume = Resume.objects.create(
        owner=user,
        title="Fit",
        template=template,
        visual_theme=template.available_themes.first(),
    )
    section = Section.objects.create(
        resume=resume,
        section_type=SectionTypeDefinition.objects.get(key="key_projects"),
    )
    content = [
        {
            "title": "Build",
            "organization": "Acme",
            "timeline": "2024",
            "summary": "",
            "bullets": ["Used Python", "Built tests"],
        }
    ]
    entry = SectionEntry.objects.create(
        section=section,
        raw_input="Used Python",
        content=content,
        content_origin="ai",
        generation_status="done",
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user, resume, section, entry


def url(sample, suffix):
    _, _, resume, section, entry = sample
    return f"/api/resumes/{resume.id}/sections/{section.id}/entries/{entry.id}/{suffix}"


@pytest.mark.parametrize("toggle", [True, False, None])
def test_generation_toggle_is_request_scoped(sample, monkeypatch, toggle):
    client, _, resume, _, entry = sample
    llm = Mock()
    llm.generate_json.return_value = entry.content
    monkeypatch.setattr("resumes.views.GeminiLLMClient", lambda: llm)
    fitter = Mock(return_value=(entry.content, {"status": "complete", "bullets": []}))
    monkeypatch.setattr("resumes.views.fit_bullets_in_content", fitter)
    # Avoid unrelated RAG dependencies/network.
    monkeypatch.setattr("resumes.views.SectionKey", [])
    response = client.post(
        url(sample, "generate/"),
        {} if toggle is None else {"fit_to_line": toggle},
        format="json",
    )
    assert response.status_code == 200
    assert fitter.call_count == (0 if toggle is False else 1)
    expected_schema = (
        get_candidate_schema(entry.section.section_type.json_schema)
        if (toggle is not False)
        else entry.section.section_type.json_schema
    )
    assert (
        llm.generate_json.call_args.kwargs["response_schema"]
        == expected_schema
    )
    resume.refresh_from_db()
    assert "fit_to_line" not in resume.config_override
    assert response.data["content_origin"] == "ai"


@pytest.mark.parametrize("toggle", [True, False])
def test_generation_lite_preprocessing_uses_one_cached_call_and_original_schema(
    sample, monkeypatch, settings, toggle
):
    from django.core.cache.backends.locmem import LocMemCache
    from resume_renderer.services import lite_preprocessing

    settings.RESUME_LLM_LITE_PREPROCESSING = True
    client, _, resume, _, entry = sample
    local_cache = LocMemCache("generation-lite-endpoint-test", {})
    local_cache.clear()
    monkeypatch.setattr(lite_preprocessing, "cache", local_cache)
    lite = Mock(provider="gemini", model="lite-test")
    lite.generate_json.return_value = {
        "contributions": [
            {
                "source_ids": [0],
                "organized_points": ["Used Python"],
            }
        ],
        "unassigned_source_ids": [],
        "ambiguities": [],
    }
    monkeypatch.setattr(lite_preprocessing, "GeminiLLMClient", Mock(return_value=lite))
    main = Mock()
    main.generate_json.return_value = entry.content
    monkeypatch.setattr("resumes.views.GeminiLLMClient", lambda: main)
    monkeypatch.setattr("resumes.views.SectionKey", [])
    fitter = Mock(return_value=(entry.content, {"status": "complete", "bullets": []}))
    monkeypatch.setattr("resumes.views.fit_bullets_in_content", fitter)
    for _ in range(2):
        response = client.post(
            url(sample, "generate/"), {"fit_to_line": toggle}, format="json"
        )
        assert response.status_code == 200
    assert lite.generate_json.call_count == 1
    assert main.generate_json.call_count == 2
    assert fitter.call_count == (2 if toggle else 0)
    expected_schema = (
        get_candidate_schema(entry.section.section_type.json_schema)
        if toggle
        else entry.section.section_type.json_schema
    )
    assert (
        main.generate_json.call_args.kwargs["response_schema"]
        == expected_schema
    )
    entry.refresh_from_db()
    assert "<lite_organization>" in entry.last_sent_prompt
    assert "<user_input>" in entry.last_sent_prompt
    assert "Used Python" in entry.last_sent_prompt
    assert entry.content == main.generate_json.return_value
    resume.refresh_from_db()
    assert "RESUME_LLM_LITE_PREPROCESSING" not in resume.config_override


def test_generation_fitter_error_is_nonfatal_and_invalid_toggle_rejected(
    sample, monkeypatch
):
    client, _, _, _, entry = sample
    llm = Mock()
    llm.generate_json.return_value = entry.content
    monkeypatch.setattr("resumes.views.GeminiLLMClient", lambda: llm)
    monkeypatch.setattr("resumes.views.SectionKey", [])
    monkeypatch.setattr(
        "resumes.views.fit_bullets_in_content", Mock(side_effect=RuntimeError())
    )
    assert (
        client.post(
            url(sample, "generate/"), {"fit_to_line": "false"}, format="json"
        ).status_code
        == 400
    )
    response = client.post(
        url(sample, "generate/"), {"fit_to_line": True}, format="json"
    )
    assert response.status_code == 200
    assert response.data["content"] == entry.content
    assert response.data["fitting"]["status"] == "partial"


def forbid_models(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("No rewriting allowed")

    monkeypatch.setattr("resumes.views.fit_bullets_in_content", forbidden)
    monkeypatch.setattr(
        "resume_renderer.services.llm_client.GeminiLLMClient.generate_json", forbidden
    )
    monkeypatch.setattr("resume_renderer.services.line_fitter.fit_entries", forbidden)


def test_manual_json_and_later_renders_keep_exact_content(sample, monkeypatch):
    client, _, resume, _, entry = sample
    forbid_models(monkeypatch)
    monkeypatch.setattr(
        "resume_renderer.services.line_fitter._extract_bullets",
        Mock(side_effect=AssertionError("Render must bypass the fitter")),
    )
    manual = copy.deepcopy(entry.content)
    manual[0]["bullets"] = ["  **Python** 20%\nchosen wording  ", ""]
    response = client.patch(url(sample, ""), {"content": manual}, format="json")
    assert response.status_code == 200
    assert response.data["content"] == manual
    assert response.data["content_origin"] == "manual"
    monkeypatch.setattr("resumes.views.compile_latex", lambda _: b"pdf")
    for _ in range(2):
        assert client.post(f"/api/resumes/{resume.id}/render/").status_code == 200
    entry.refresh_from_db()
    assert entry.content == manual
    assert entry.fitting == {}


@pytest.mark.parametrize("operation", ["font", "spacing", "template"])
def test_layout_changes_never_rewrite(sample, monkeypatch, operation):
    client, _, resume, _, entry = sample
    before = copy.deepcopy(entry.content)
    forbid_models(monkeypatch)
    monkeypatch.setattr("resumes.views.compile_latex", lambda _: b"pdf")
    monkeypatch.setattr(
        "resumes.services.template_switch.compile_latex", lambda _: b"pdf"
    )
    if operation == "template":
        response = client.post(
            f"/api/resumes/{resume.id}/template/",
            {"template_key": "awesome-cv-general"},
            format="json",
        )
    else:
        response = client.patch(
            f"/api/resumes/{resume.id}/style/",
            {"font": "times"}
            if operation == "font"
            else {"word_spacing": "1.15", "line_spacing": "1.10"},
            format="json",
        )
    assert response.status_code == 200
    entry.refresh_from_db()
    assert entry.content == before


def fake_fit(resume, entries, llm):
    results = {}
    for eid, (_, content) in entries.items():
        reports = [
            {
                "path": [0, "bullets", i],
                "original": t,
                "text": t + " revised",
                "status": "fitted",
                "attempts": 1,
                "measurement": None,
                "original_measurement": None,
                "reason": "",
            }
            for i, t in enumerate(content[0]["bullets"])
        ]
        results[eid] = {
            "content": content,
            "fitting": {"status": "complete", "bullets": reports},
        }
    return results


def test_project_summary_refit_requires_review_and_preserves_manual_origin(
    sample, monkeypatch
):
    client, _, resume, _, entry = sample
    original = "A long project summary that wraps across two rendered lines"
    proposed = "A concise project summary"
    entry.content[0]["summary"] = original
    entry.content_origin = "manual"
    entry.save(update_fields=["content", "content_origin"])

    def summary_fit(_resume, entries, _llm):
        if not entries:
            return {}
        eid = str(entry.id)
        return {
            eid: {
                "content": entries[eid][1],
                "fitting": {
                    "status": "complete",
                    "bullets": [],
                    "summaries": [
                        {
                            "kind": "summary",
                            "path": [0, "summary", 0],
                            "original": original,
                            "text": proposed,
                            "proposed_bullets": [proposed],
                            "status": "fitted",
                            "attempts": 1,
                            "measurement": None,
                            "original_measurement": None,
                            "reason": "",
                        }
                    ],
                },
            }
        }

    monkeypatch.setattr(refit, "fit_entries", summary_fit)
    monkeypatch.setattr(refit, "GeminiLLMClient", Mock())
    path = f"/api/resumes/{resume.id}/refit/preview/"
    excluded = client.post(path, {}, format="json")
    assert excluded.data["proposals"] == []
    preview = client.post(path, {"include_manual": True}, format="json")
    assert preview.data["proposals"][0]["kind"] == "summary"
    entry.refresh_from_db()
    assert entry.content[0]["summary"] == original
    monkeypatch.setattr(refit, "compile_latex", lambda _: b"pdf")
    applied = client.post(
        f"/api/resumes/{resume.id}/refit/apply/",
        {"token": preview.data["token"], "selected_ids": ["0"]},
        format="json",
    )
    assert applied.status_code == 200
    entry.refresh_from_db()
    assert entry.content[0]["summary"] == proposed
    assert entry.content_origin == "manual"


@pytest.mark.parametrize("origin", ["manual", "unknown"])
def test_protected_origins_excluded_unless_explicitly_included(
    sample, monkeypatch, origin
):
    client, _, resume, _, entry = sample
    entry.content_origin = origin
    entry.save()
    monkeypatch.setattr(refit, "GeminiLLMClient", Mock())
    fitter = Mock(side_effect=fake_fit)
    monkeypatch.setattr(refit, "fit_entries", fitter)
    path = f"/api/resumes/{resume.id}/refit/preview/"
    first = client.post(path, {}, format="json").data
    assert first["excluded_entries"] == 1
    assert not first["proposals"]
    second = client.post(path, {"include_manual": True}, format="json").data
    assert len(second["proposals"]) == 2
    entry.refresh_from_db()
    assert entry.content[0]["bullets"] == ["Used Python", "Built tests"]
    monkeypatch.setattr(refit, "compile_latex", lambda _: b"pdf")
    applied = client.post(
        f"/api/resumes/{resume.id}/refit/apply/",
        {"token": second["token"], "selected_ids": ["0"]},
        format="json",
    )
    assert applied.status_code == 200
    entry.refresh_from_db()
    assert entry.content[0]["bullets"] == ["Used Python revised", "Built tests"]
    assert entry.content_origin == origin


@pytest.mark.parametrize(
    "change",
    ["content", "style", "template", "expired", "tampered", "owner", "compile"],
)
def test_stale_invalid_and_compile_failure_do_not_apply(sample, monkeypatch, change):
    client, user, resume, _, entry = sample
    monkeypatch.setattr(refit, "fit_entries", fake_fit)
    monkeypatch.setattr(refit, "GeminiLLMClient", Mock())
    result = client.post(
        f"/api/resumes/{resume.id}/refit/preview/", {}, format="json"
    ).data
    token = result["token"]
    if change == "content":
        entry.raw_input = "Changed"
        entry.save()
    elif change == "style":
        resume.config_override = {"style": {"font": "times"}}
        resume.save()
    elif change == "template":
        resume.template = ResumeTemplate.objects.get(key="iitb-general")
        resume.save()
    elif change == "expired":
        monkeypatch.setattr(signing.time, "time", lambda: 9999999999)
    elif change == "tampered":
        token += "invalid"
    elif change == "owner":
        payload = signing.loads(token, salt=refit.SALT)
        payload["user"] = str(user.pk + 1)
        token = signing.dumps(payload, salt=refit.SALT)
    elif change == "compile":
        monkeypatch.setattr(refit, "compile_latex", Mock(side_effect=RuntimeError()))
    monkeypatch.setattr(
        refit, "fit_entries", Mock(side_effect=AssertionError("Apply cannot refit"))
    )
    response = client.post(
        f"/api/resumes/{resume.id}/refit/apply/",
        {"token": token, "selected_ids": ["0"]},
        format="json",
    )
    assert response.status_code == (422 if change == "compile" else 409)
    entry.refresh_from_db()
    assert entry.content[0]["bullets"] == ["Used Python", "Built tests"]


def test_duplicates_preserve_protection(sample):
    client, _, resume, _, entry = sample
    entry.content_origin = "manual"
    entry.save()
    response = client.post(f"/api/resumes/{resume.id}/duplicate/")
    assert response.status_code == 201
    assert response.data["sections"][0]["entries"][0]["content_origin"] == "manual"


def test_preview_reports_service_failure_once_and_keeps_saved_content(
    sample, monkeypatch
):
    from resume_renderer.services import line_fitter
    from resume_renderer.services.llm_client import LLMClientError

    client, _, resume, _, entry = sample
    llm = Mock()
    llm.generate_json.side_effect = LLMClientError(
        "Provider private response", code=503
    )
    monkeypatch.setattr(refit, "GeminiLLMClient", lambda: llm)
    monkeypatch.setattr(
        line_fitter,
        "measure_entries",
        lambda r, entries: {
            (eid, *ref[:3]): {
                "ratio": 0.5,
                "width_pt": 200,
                "available_pt": 400,
                "lines": 1,
            }
            for eid, (section, content) in entries.items()
            for ref in line_fitter._extract_bullets(content, section)
        },
    )
    before = copy.deepcopy(entry.content)
    response = client.post(
        f"/api/resumes/{resume.id}/refit/preview/", {}, format="json"
    )
    assert response.status_code == 200
    assert response.data["proposals"] == []
    assert len(response.data["errors"]) == 1
    assert response.data["errors"][0]["code"] == "model_unavailable"
    assert "503" in response.data["errors"][0]["message"]
    entry.refresh_from_db()
    assert entry.content == before


@pytest.mark.parametrize(
    "selected,expected",
    [
        (["0"], ["Built Python parser", "Evaluated outputs", "Built tests"]),
        (["0", "1"], ["Built Python parser", "Evaluated outputs", "Tested outputs"]),
    ],
)
def test_refit_split_is_reviewed_and_applied_at_original_indexes(
    sample, monkeypatch, selected, expected
):
    client, _, resume, _, entry = sample

    def split_fit(_resume, entries, _llm):
        eid = str(entry.id)
        return {
            eid: {
                "content": entries[eid][1],
                "fitting": {
                    "status": "complete",
                    "bullets": [
                        {
                            "path": [0, "bullets", 0],
                            "original": "Used Python",
                            "text": "Built Python parser\nEvaluated outputs",
                            "proposed_bullets": [
                                "Built Python parser",
                                "Evaluated outputs",
                            ],
                            "measurements": [],
                            "status": "fitted",
                            "attempts": 1,
                            "measurement": None,
                            "original_measurement": None,
                            "reason": "",
                            "action": "split",
                            "dropped": [],
                            "added": [],
                        },
                        {
                            "path": [0, "bullets", 1],
                            "original": "Built tests",
                            "text": "Tested outputs",
                            "proposed_bullets": ["Tested outputs"],
                            "status": "fitted",
                            "attempts": 1,
                            "measurement": None,
                            "original_measurement": None,
                            "reason": "",
                            "action": "rewrite",
                            "dropped": [],
                            "added": [],
                        },
                    ],
                },
            }
        }

    monkeypatch.setattr(refit, "fit_entries", split_fit)
    monkeypatch.setattr(refit, "GeminiLLMClient", Mock())
    monkeypatch.setattr(refit, "compile_latex", lambda _: b"pdf")
    preview = client.post(f"/api/resumes/{resume.id}/refit/preview/", {}, format="json")
    assert preview.status_code == 200
    assert preview.data["proposals"][0]["proposed_bullets"] == [
        "Built Python parser",
        "Evaluated outputs",
    ]
    entry.refresh_from_db()
    assert entry.content[0]["bullets"] == ["Used Python", "Built tests"]
    applied = client.post(
        f"/api/resumes/{resume.id}/refit/apply/",
        {"token": preview.data["token"], "selected_ids": selected},
        format="json",
    )
    assert applied.status_code == 200
    entry.refresh_from_db()
    assert entry.content[0]["bullets"] == expected
