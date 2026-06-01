import json
import pytest
from rest_framework.test import APIClient


class DummyResp:
    def __init__(self, status, data):
        self.status_code = status
        self._data = data

    def json(self):
        return self._data


@pytest.mark.django_db
def test_create_and_list_resume(monkeypatch):
    # Mock REACH verify to accept token and return username
    def fake_get(url, headers=None, timeout=None):
        return DummyResp(200, {"user": "testuser", "id": 123, "role": "student"})

    monkeypatch.setattr("server.utils.token_dec.requests.get", fake_get)

    client = APIClient()
    token = "fake-token"
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    payload = {
        "title": "My Resume",
        "resume_type": "ONE",
        "header_type": "SHORT",
        "sections": [
            {
                "section_type": "EXPERIENCE",
                "order": 0,
                "content": [{"title": "Intern", "bullets": ["did stuff"]}],
            }
        ],
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

    monkeypatch.setattr("server.utils.token_dec.requests.get", fake_get)

    client = APIClient()
    token = "fake-token-2"
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    payload = {
        "title": "Resume to update",
        "resume_type": "ONE",
        "header_type": "SHORT",
    }
    resp = client.post(
        "/api/resumes/", data=json.dumps(payload), content_type="application/json"
    )
    assert resp.status_code == 201
    rid = resp.json()["id"]

    # Patch: add a section
    patch_payload = {
        "sections": [
            {
                "section_type": "EXPERIENCE",
                "order": 0,
                "content": [{"title": "Job", "bullets": ["x"]}],
            }
        ]
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
