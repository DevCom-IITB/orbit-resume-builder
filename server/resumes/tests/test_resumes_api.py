import json
import pytest
from rest_framework.test import APIClient

# Template and theme created by migration 0004 (and refreshed by seed_templates).
TEMPLATE_KEY = "iitb-general"
THEME_KEY = "iitb-classic"


class DummyResp:
    def __init__(self, status, data):
        self.status_code = status
        self._data = data

    def json(self):
        return self._data


def _client_for(monkeypatch, username):
    """APIClient whose Bearer token REACH (mocked) verifies as `username`."""

    def fake_get(url, headers=None, timeout=None):
        return DummyResp(200, {"user": username, "id": 1, "role": "student"})

    monkeypatch.setattr("utils.token_dec.requests.get", fake_get)

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer token-for-{username}")
    return client


def _create(client, title, **extra):
    payload = {
        "title": title,
        "template_key": TEMPLATE_KEY,
        "visual_theme_key": THEME_KEY,
        **extra,
    }
    return client.post(
        "/api/resumes/", data=json.dumps(payload), content_type="application/json"
    )


@pytest.mark.django_db
def test_create_and_list_resume(monkeypatch):
    client = _client_for(monkeypatch, "testuser")

    resp = _create(client, "My Resume")
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "My Resume"
    assert data["template"]["key"] == TEMPLATE_KEY
    # Default sections come from the template manifest.
    section_keys = {s["section_type"]["key"] for s in data["sections"]}
    assert {"header", "education"} <= section_keys

    # list
    resp2 = client.get("/api/resumes/")
    assert resp2.status_code == 200
    out = resp2.json()
    assert out["count"] == 1


@pytest.mark.django_db
def test_patch_creates_version_and_delete(monkeypatch):
    client = _client_for(monkeypatch, "testuser2")

    resp = _create(client, "Resume to update")
    assert resp.status_code == 201
    rid = resp.json()["id"]

    resp2 = client.patch(
        f"/api/resumes/{rid}/",
        data=json.dumps({"title": "Updated title"}),
        content_type="application/json",
    )
    assert resp2.status_code == 200
    assert resp2.json()["title"] == "Updated title"
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
    client = _client_for(monkeypatch, "pinner")

    resp_a = _create(client, "Resume A")
    assert resp_a.status_code == 201
    id_a = resp_a.json()["id"]

    resp_b = _create(client, "Resume B", pages=2)
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
    client = _client_for(monkeypatch, "duplicator")

    resp = _create(client, "Original Resume")
    assert resp.status_code == 201
    source = resp.json()

    resp_dup = client.post(f"/api/resumes/{source['id']}/duplicate/")
    assert resp_dup.status_code == 201
    dup = resp_dup.json()
    assert dup["title"] == "Original Resume (Copy)"
    assert dup["is_pinned"] is False
    assert dup["id"] != source["id"]

    def section_keys(resume):
        return sorted(s["section_type"]["key"] for s in resume["sections"])

    assert section_keys(dup) == section_keys(source)
    assert {s["id"] for s in dup["sections"]}.isdisjoint(
        {s["id"] for s in source["sections"]}
    )
