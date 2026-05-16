import json

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient


@pytest.fixture()
def api_client():
    return APIClient()


@pytest.fixture()
def user(db):
    return get_user_model().objects.create_user(username="user", password="pass")


def test_render_rejects_invalid_json(api_client, user):
    api_client.force_authenticate(user=user)
    response = api_client.post(
        "/api/resume-renderer/render/",
        data="{",
        content_type="application/json",
    )
    assert response.status_code == 400
    assert response.data["error"] == "Invalid JSON payload."


def test_render_defaults_config(api_client, user, monkeypatch):
    api_client.force_authenticate(user=user)

    def fake_compile(_latex):
        return b"%PDF-1.4"

    monkeypatch.setattr("resume_renderer.services.renderer.compile_latex", fake_compile)

    payload = {
        "header": {
            "name": "Jane Doe",
            "edu": "B.Tech",
            "contact": {
                "email": "jane@example.com",
                "phone": "+1 555 000",
                "linkedin": "jane-doe",
                "github": "janedoe",
            },
        },
        "education": [],
        "experience": [],
        "key_projects": [],
    }

    response = api_client.post(
        "/api/resume-renderer/render/",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"


def test_render_rejects_bad_bullets(api_client, user):
    api_client.force_authenticate(user=user)

    payload = {
        "experience": [
            {
                "title": "Intern",
                "organisation": "ACME",
                "location": "Remote",
                "timeline": "2024",
                "bullets": "not-a-list",
            }
        ]
    }

    response = api_client.post(
        "/api/resume-renderer/render/",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "bullets" in str(response.data)
