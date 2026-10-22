"""Regression tests for the critical fixes in out.md (1.1, 1.5, 1.6, 2.2)."""

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework.test import APIClient

from resumes.models import Resume, Version
from resume_renderer.services import renderer


@pytest.fixture
def user(db):
    call_command("seed_templates", verbosity=0)
    return get_user_model().objects.create_user(username="alice", password="x")


@pytest.fixture
def client(user):
    api_client = APIClient()
    api_client.force_authenticate(user=user)
    return api_client


def _create_resume(client):
    resp = client.post(
        "/api/resumes/",
        {
            "title": "My Resume",
            "template_key": "iitb-general",
            "visual_theme_key": "iitb-classic",
        },
        format="json",
    )
    assert resp.status_code == 201, resp.content
    return resp.json()


def _section(resume_json, key):
    return next(s for s in resume_json["sections"] if s["section_type"]["key"] == key)


# --- 1.1: generation used an undefined `LLMClient` -------------------------


def test_generate_entry_uses_llm_client(client, monkeypatch):
    class FakeLLMClient:
        def generate_json(self, prompt):
            return [{"category": "Languages", "skills": ["Python", "C++"]}]

    monkeypatch.setattr("resumes.views.LLMClient", FakeLLMClient)
    monkeypatch.setattr(
        "resumes.views.fit_bullets_in_content", lambda content, key, llm: content
    )

    resume = _create_resume(client)
    section = _section(resume, "technical_skills")
    base = f"/api/resumes/{resume['id']}/sections/{section['id']}/entries/"
    entry = client.post(base, {"raw_input": "python, c++"}, format="json").json()

    resp = client.post(f"{base}{entry['id']}/generate/")

    assert resp.status_code == 200, resp.content
    assert resp.json()["generation_status"] == "done"
    assert resp.json()["content"][0]["skills"] == ["Python", "C++"]


# --- 1.5: themes ?family= used a JSONField lookup SQLite doesn't support ----


def test_themes_filter_by_family(client):
    resp = client.get("/api/resumes/themes/", {"family": "iitb"})

    assert resp.status_code == 200
    keys = {t["key"] for t in resp.json()}
    assert "iitb-classic" in keys
    assert "external-standard" not in keys


# --- 1.6: edits that change the PDF must drop the LaTeX cache --------------


def _mark_cache_valid(resume_id):
    Resume.objects.filter(id=resume_id).update(
        latex_cache_valid=True, cached_latex="% renderer-v2\nstale"
    )


def _cache_valid(resume_id):
    return Resume.objects.get(id=resume_id).latex_cache_valid


def test_section_reorder_invalidates_cache(client):
    resume = _create_resume(client)
    section = _section(resume, "technical_skills")
    _mark_cache_valid(resume["id"])

    client.patch(
        f"/api/resumes/{resume['id']}/sections/{section['id']}/",
        {"order": 99},
        format="json",
    )

    assert not _cache_valid(resume["id"])


def test_entry_reorder_invalidates_cache(client):
    resume = _create_resume(client)
    section = _section(resume, "technical_skills")
    base = f"/api/resumes/{resume['id']}/sections/{section['id']}/entries/"
    entry = client.post(base, {"raw_input": "x"}, format="json").json()
    _mark_cache_valid(resume["id"])

    client.patch(f"{base}{entry['id']}/", {"order": 5}, format="json")

    assert not _cache_valid(resume["id"])


@pytest.mark.parametrize(
    "patch", [{"pages": 2}, {"config_override": {"header_style": "long"}}]
)
def test_resume_render_fields_invalidate_cache(client, patch):
    resume = _create_resume(client)
    _mark_cache_valid(resume["id"])

    client.patch(f"/api/resumes/{resume['id']}/", patch, format="json")

    assert not _cache_valid(resume["id"])


def test_title_change_keeps_cache(client):
    resume = _create_resume(client)
    _mark_cache_valid(resume["id"])

    client.patch(f"/api/resumes/{resume['id']}/", {"title": "New"}, format="json")

    assert _cache_valid(resume["id"])


def test_assembled_latex_is_reused_from_cache(client):
    resume_json = _create_resume(client)
    resume = Resume.objects.get(id=resume_json["id"])

    first = renderer.assemble_resume_latex(resume)
    resume.refresh_from_db()
    assert resume.latex_cache_valid

    # Change the stored LaTeX: a cache hit must return it unchanged.
    Resume.objects.filter(id=resume.id).update(cached_latex=first + "\n% cached")
    resume.refresh_from_db()
    assert renderer.assemble_resume_latex(resume).endswith("% cached")


# --- 2.2: version snapshots nested every earlier snapshot ------------------


def test_version_snapshot_excludes_versions(client):
    resume = _create_resume(client)
    for i in range(3):
        client.patch(f"/api/resumes/{resume['id']}/", {"title": f"T{i}"}, format="json")

    versions = Version.objects.filter(resume_id=resume["id"])
    assert versions.count() == 3
    for version in versions:
        assert "versions" not in version.snapshot


def test_pin_toggle_creates_no_version(client):
    resume = _create_resume(client)

    client.patch(f"/api/resumes/{resume['id']}/", {"is_pinned": True}, format="json")

    assert not Version.objects.filter(resume_id=resume["id"]).exists()
