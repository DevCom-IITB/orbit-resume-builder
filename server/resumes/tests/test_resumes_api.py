import json
import pytest
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from resumes.models import ResumeTemplate, VisualTheme, SectionTypeDefinition, TemplateSectionType


class DummyResp:
    def __init__(self, status, data):
        self.status_code = status
        self._data = data

    def json(self):
        return self._data


@pytest.fixture(autouse=True)
def base_resume_setup(db):
    theme, _ = VisualTheme.objects.get_or_create(
        key="iitb-classic",
        defaults={
            "display_name": "IITB Classic",
            "compatible_families": ["iitb"],
            "converter_set_key": "iitb",
            "latex_preamble": r"\documentclass{article}\begin{document}__CONTENT__\end{document}",
        },
    )
    tmpl, _ = ResumeTemplate.objects.get_or_create(
        key="iitb-general",
        defaults={
            "display_name": "IITB General",
            "family": "iitb",
            "domain": "general",
            "max_pages": 2,
            "template_config": {},
            "is_active": True,
        },
    )
    tmpl.available_themes.set([theme])

    sec_type, _ = SectionTypeDefinition.objects.get_or_create(
        key="experience",
        defaults={
            "display_name": "Experience",
            "allow_multiple_entries": True,
            "json_schema": {"type": "array"},
        },
    )
    TemplateSectionType.objects.get_or_create(
        template=tmpl,
        section_type=sec_type,
        defaults={"default_order": 0, "is_default": True},
    )


@pytest.mark.django_db
def test_create_and_list_resume(monkeypatch):
    def fake_get(url, headers=None, timeout=None):
        return DummyResp(200, {"user": "testuser", "id": 123, "role": "student"})

    monkeypatch.setattr("utils.token_dec.requests.get", fake_get)

    client = APIClient()
    token = "fake-token"
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    payload = {
        "title": "My Resume",
        "template_key": "iitb-general",
        "visual_theme_key": "iitb-classic",
        "pages": 1,
    }

    resp = client.post(
        "/api/resumes/", data=json.dumps(payload), content_type="application/json"
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "My Resume"

    # list
    resp2 = client.get("/api/resumes/")
    assert resp2.status_code == 200
    out = resp2.json()
    assert out["count"] == 1


@pytest.mark.django_db
def test_patch_creates_version_and_delete(monkeypatch):
    def fake_get(url, headers=None, timeout=None):
        return DummyResp(200, {"user": "testuser2", "id": 234, "role": "student"})

    monkeypatch.setattr("utils.token_dec.requests.get", fake_get)

    client = APIClient()
    token = "fake-token-2"
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    payload = {
        "title": "Resume to update",
        "template_key": "iitb-general",
        "visual_theme_key": "iitb-classic",
        "pages": 1,
    }
    resp = client.post(
        "/api/resumes/", data=json.dumps(payload), content_type="application/json"
    )
    assert resp.status_code == 201
    rid = resp.json()["id"]

    # Patch: update title
    patch_payload = {
        "title": "Updated Resume Title",
    }
    resp2 = client.patch(
        f"/api/resumes/{rid}/",
        data=json.dumps(patch_payload),
        content_type="application/json",
    )
    assert resp2.status_code == 200
    # versions should have one entry
    detail = client.get(f"/api/resumes/{rid}/").json()
    assert len(detail.get("versions", [])) == 1

    # delete
    resp3 = client.delete(f"/api/resumes/{rid}/")
    assert resp3.status_code == 204
    # now list should be 0 for this user
    resp4 = client.get("/api/resumes/")
    assert resp4.status_code == 200
    assert resp4.json()["count"] == 0


@pytest.mark.django_db
def test_pin_toggle_and_list_order(monkeypatch):
    def fake_get(url, headers=None, timeout=None):
        return DummyResp(200, {"user": "pinner", "id": 345, "role": "student"})

    monkeypatch.setattr("utils.token_dec.requests.get", fake_get)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Bearer fake-token-pin")

    payload = {
        "title": "Resume A",
        "template_key": "iitb-general",
        "visual_theme_key": "iitb-classic",
        "pages": 1,
    }
    resp_a = client.post(
        "/api/resumes/", data=json.dumps(payload), content_type="application/json"
    )
    assert resp_a.status_code == 201
    id_a = resp_a.json()["id"]

    payload_b = {
        "title": "Resume B",
        "template_key": "iitb-general",
        "visual_theme_key": "iitb-classic",
        "pages": 2,
    }
    resp_b = client.post(
        "/api/resumes/", data=json.dumps(payload_b), content_type="application/json"
    )
    assert resp_b.status_code == 201
    id_b = resp_b.json()["id"]

    resp_pin = client.patch(
        f"/api/resumes/{id_b}/",
        data=json.dumps({"is_pinned": True}),
        content_type="application/json",
    )
    assert resp_pin.status_code == 200
    assert resp_pin.json()["is_pinned"] is True

    resp_list = client.get("/api/resumes/")
    results = resp_list.json()["results"]
    assert results[0]["id"] == id_b
    assert results[0]["is_pinned"] is True
    assert results[1]["id"] == id_a


@pytest.mark.django_db
def test_duplicate_creates_copy_with_sections(monkeypatch):
    def fake_get(url, headers=None, timeout=None):
        return DummyResp(200, {"user": "duplicator", "id": 456, "role": "student"})

    monkeypatch.setattr("utils.token_dec.requests.get", fake_get)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Bearer fake-token-dup")

    payload = {
        "title": "Original Resume",
        "template_key": "iitb-general",
        "visual_theme_key": "iitb-classic",
        "pages": 1,
    }
    resp = client.post(
        "/api/resumes/", data=json.dumps(payload), content_type="application/json"
    )
    assert resp.status_code == 201
    source_id = resp.json()["id"]

    resp_dup = client.post(f"/api/resumes/{source_id}/duplicate/")
    assert resp_dup.status_code == 201
    dup = resp_dup.json()
    assert dup["title"] == "Original Resume (Copy)"
    assert dup["is_pinned"] is False
    assert dup["id"] != source_id
    assert len(dup["sections"]) >= 1

    source = client.get(f"/api/resumes/{source_id}/").json()
    assert source["title"] == "Original Resume"
    assert len(source["sections"]) >= 1
