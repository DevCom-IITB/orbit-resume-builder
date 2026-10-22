import base64
import json

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from resume_renderer.JSONSchema.jsonschema import get_schema


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
    data = response.json()
    pdf_bytes = base64.b64decode(data["pdf"])

    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"
    assert pdf_bytes.startswith(b"%PDF-1.4")


def test_render_rejects_bad_bullets(api_client, user):
    api_client.force_authenticate(user=user)

    payload = {
        "experience": [
            {
                "title": "Intern",
                "organization": "ACME",
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


def test_refine_key_projects_uses_static_llm_response(api_client, user, monkeypatch):
    api_client.force_authenticate(user=user)
    seen = {}
    jsonschema = pytest.importorskip("jsonschema")

    class FakeGeminiLLMClient:
        def generate_json(self, prompt):
            seen["prompt"] = prompt
            return [
                {
                    "title": "AI Resume Builder",
                    "organization": "DevCom, IIT Bombay",
                    "summary": "An AI-powered web application that turns rough user input into polished resume content and generated PDFs.",
                    "timeline": "May 2026",
                    "bullets": [
                        "Built a full-stack resume builder with React and Django to convert rough student inputs into structured resume content.",
                        "Implemented a LaTeX PDF generation flow to render polished resumes from the refined JSON output.",
                    ],
                }
            ]

    monkeypatch.setattr("resume_renderer.views.GeminiLLMClient", FakeGeminiLLMClient)

    payload = {
        "user_input": (
            "made ai resume builder project using react django and latex where user enters rough points "
            "and the system converts them into resume bullets and pdf is generated"
        )
    }

    response = api_client.post(
        "/api/resume-renderer/key_projects/",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.data["success"] is True
    assert response.data["section_type"] == "key_projects"
    jsonschema.validate(
        instance=response.data["data"], schema=get_schema("key_projects")
    )
    assert "made ai resume builder project" in seen["prompt"].lower()


def test_render_accepts_new_sections_and_passes_latex(api_client, user, monkeypatch):
    api_client.force_authenticate(user=user)
    seen = {}

    def fake_compile(latex):
        seen["latex"] = latex
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
        "education": [
            {
                "degree": "B.Tech",
                "institution": "IIT",
                "cpi": "9.1",
                "year": "2021-2025",
            }
        ],
        "experience": [
            {
                "title": "Intern",
                "organization": "ACME",
                "location": "Remote",
                "timeline": "2024",
                "bullets": ["Did work"],
            }
        ],
        "key_projects": [
            {
                "title": "Project X",
                "organization": "Prof Y",
                "summary": "Summary",
                "timeline": "2024",
                "bullets": ["Built thing"],
            }
        ],
        "pors": [
            {
                "role": "Developer",
                "organization": "DevCom",
                "duration": "2025",
                "summary": "Summary",
                "bullets": ["Led module"],
            }
        ],
        "scholastic_achievements": ["Achieved rank"],
        "courses": [
            {
                "category": "CS",
                "courses": ["DSA"],
            }
        ],
        "technical_skills": [
            {
                "category": "Programming",
                "skills": ["Python"],
            }
        ],
    }

    response = api_client.post(
        "/api/resume-renderer/render/",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response["Content-Type"] == "application/json"
    assert "KEY PROJECTS" in seen["latex"]
    assert "COURSES UNDERTAKEN" in seen["latex"]
    assert "TECHNICAL SKILLS" in seen["latex"]


def test_render_rejects_invalid_courses_shape(api_client, user):
    api_client.force_authenticate(user=user)

    payload = {
        "courses": [
            {
                "category": "CS",
                "courses": "not-a-list",
            }
        ]
    }

    response = api_client.post(
        "/api/resume-renderer/render/",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "courses" in str(response.data).lower()


def test_render_without_header_skips_it(api_client, user, monkeypatch):
    # The editor has no header section, so renders arrive with no "header" key.
    api_client.force_authenticate(user=user)
    seen = {}

    def fake_compile(latex):
        seen["latex"] = latex
        return b"%PDF-1.4"

    monkeypatch.setattr("resume_renderer.services.renderer.compile_latex", fake_compile)

    payload = {"scholastic_achievements": ["Ranked 1st in a contest"]}
    response = api_client.post(
        "/api/resume-renderer/render/",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert "SCHOLASTIC ACHIEVEMENTS" in seen["latex"]
    assert "\\begin{center}" not in seen["latex"]


def test_render_converter_error_returns_400(api_client, user, monkeypatch):
    api_client.force_authenticate(user=user)
    monkeypatch.setattr(
        "resume_renderer.services.renderer.compile_latex", lambda _latex: b""
    )

    # Passes the serializer (bullets are valid) but lacks keys the converter needs.
    payload = {"experience": [{"bullets": ["did stuff"]}]}
    response = api_client.post(
        "/api/resume-renderer/render/",
        data=json.dumps(payload),
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "Missing key" in response.data["error"]


class _DummyResp:
    def __init__(self, status_code, data):
        self.status_code = status_code
        self._data = data

    def json(self):
        return self._data


def test_render_accepts_reach_bearer_token(api_client, db, monkeypatch):
    monkeypatch.setattr(
        "utils.token_dec.requests.get",
        lambda *a, **kw: _DummyResp(200, {"user": "reachuser"}),
    )
    monkeypatch.setattr(
        "resume_renderer.services.renderer.compile_latex", lambda _latex: b"%PDF"
    )
    api_client.credentials(HTTP_AUTHORIZATION="Bearer some-token")

    response = api_client.post(
        "/api/resume-renderer/render/",
        data=json.dumps({"scholastic_achievements": ["x"]}),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert get_user_model().objects.filter(username="reachuser").exists()


def test_render_rejects_bad_reach_token_with_401(api_client, db, monkeypatch):
    monkeypatch.setattr(
        "utils.token_dec.requests.get",
        lambda *a, **kw: _DummyResp(401, {"detail": "bad"}),
    )
    api_client.credentials(HTTP_AUTHORIZATION="Bearer bad-token")

    response = api_client.post(
        "/api/resume-renderer/render/",
        data=json.dumps({}),
        content_type="application/json",
    )

    assert response.status_code == 401


def test_render_without_token_returns_401(api_client, db):
    response = api_client.post(
        "/api/resume-renderer/render/",
        data=json.dumps({}),
        content_type="application/json",
    )

    assert response.status_code == 401
