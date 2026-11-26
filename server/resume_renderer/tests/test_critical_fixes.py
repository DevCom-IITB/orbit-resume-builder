"""Regression tests for the critical fixes in out.md (1.3, 1.4, 2.1, 3.1, 3.3-3.6)."""

import json

import pytest
import requests
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APIClient

from resume_renderer.services import line_fitter, renderer


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(username="bob", password="x")


class _Resp:
    def __init__(self, status_code, data):
        self.status_code = status_code
        self._data = data

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


# --- 1.4: legacy /render/ compiled fragments with no \documentclass ---------


def test_legacy_render_wraps_fragments_in_template(api_client, user, monkeypatch):
    api_client.force_authenticate(user=user)
    seen = {}

    def fake_compile(latex):
        seen["latex"] = latex
        return b"%PDF"

    monkeypatch.setattr("resume_renderer.services.renderer.compile_latex", fake_compile)

    resp = api_client.post(
        "/api/resume-renderer/render/",
        data=json.dumps({"technical_skills": [{"category": "L", "skills": ["Py"]}]}),
        content_type="application/json",
    )

    assert resp.status_code == 200, resp.content
    assert "\\documentclass" in seen["latex"]
    assert "__CONTENT__" not in seen["latex"]
    assert seen["latex"].rstrip().endswith("\\end{document}")


# --- 3.3: the LLM refine endpoint had no auth --------------------------------


def test_refine_requires_auth(api_client, db):
    resp = api_client.post(
        "/api/resume-renderer/key_projects/",
        data=json.dumps({"user_input": "built a thing"}),
        content_type="application/json",
    )

    assert resp.status_code == 401


# --- 3.4 / 3.1: SSO OAuth state and token delivery ---------------------------


def test_sso_login_stores_random_state(api_client, db):
    first = api_client.get("/api/sso/accounts/login/")
    state1 = api_client.session["sso_oauth_state"]
    api_client.get("/api/sso/accounts/login/")
    state2 = api_client.session["sso_oauth_state"]

    assert first.status_code == 302
    assert f"state={state1}" in first["Location"]
    assert state1 != state2
    assert "secure_random_state" not in first["Location"]


def test_sso_callback_rejects_bad_state(api_client, db):
    api_client.get("/api/sso/accounts/login/")

    resp = api_client.get("/api/sso/accounts/callback/", {"code": "c", "state": "forged"})

    assert resp.status_code == 400


def test_sso_callback_rejects_missing_session_state(api_client, db):
    resp = api_client.get("/api/sso/accounts/callback/", {"code": "c", "state": "x"})

    assert resp.status_code == 400


@override_settings(REACH_ORIGINS=["https://reach.example"])
def test_sso_callback_posts_token_only_to_reach(api_client, db, monkeypatch):
    monkeypatch.setattr("ssoAuth.views._basic_auth_token", lambda: "basic")
    monkeypatch.setattr(
        "ssoAuth.views.requests.post",
        lambda *a, **kw: _Resp(200, {"access_token": "gymkhana-token"}),
    )
    monkeypatch.setattr(
        "ssoAuth.views.requests.get",
        lambda *a, **kw: _Resp(
            200,
            {"username": "carol", "email": "c@x", "first_name": "</script><b>", "last_name": ""},
        ),
    )
    api_client.get("/api/sso/accounts/login/")
    state = api_client.session["sso_oauth_state"]

    resp = api_client.get("/api/sso/accounts/callback/", {"code": "c", "state": state})
    html = resp.content.decode()

    assert resp.status_code == 200
    assert "'*'" not in html
    assert '["https://reach.example"]' in html
    assert "refresh" not in html
    # State is single-use.
    assert "sso_oauth_state" not in api_client.session


# --- 3.6: service key ---------------------------------------------------------


def _verify(api_client, user, key):
    api_client.force_authenticate(user=user)
    headers = {"HTTP_X_SERVICE_KEY": key} if key is not None else {}
    return api_client.get("/api/sso/accounts/verify/", **headers)


@override_settings(RB_SERVICE_KEY="secret-key")
def test_verify_accepts_correct_service_key(api_client, user):
    assert _verify(api_client, user, "secret-key").status_code == 200


@override_settings(RB_SERVICE_KEY="secret-key")
def test_verify_rejects_wrong_service_key(api_client, user):
    assert _verify(api_client, user, "dev-resume-key-1").status_code == 403


@override_settings(RB_SERVICE_KEY="")
def test_verify_fails_closed_without_service_key(api_client, user):
    assert _verify(api_client, user, "").status_code == 503


# --- 1.3 / 3.5: GitHub OAuth ---------------------------------------------------

GITHUB_ON = dict(
    GITHUB_ENABLED=True,
    GITHUB_CLIENT_ID="cid",
    GITHUB_CLIENT_SECRET="secret",
    GITHUB_REDIRECT_URI="http://localhost/cb/",
    GITHUB_OAUTH_SCOPE="read:user",
)


@override_settings(GITHUB_ENABLED=False)
def test_github_connect_without_config_returns_503(api_client, db):
    assert api_client.get("/api/resume-renderer/github/connect/").status_code == 503


@override_settings(**GITHUB_ON)
def test_github_connect_uses_session_state_and_narrow_scope(api_client, db):
    resp = api_client.get("/api/resume-renderer/github/connect/")
    url = resp.json()["authorization_url"]
    state = api_client.session["github_oauth_state"]

    assert f"state={state}" in url
    assert "scope=read%3Auser" in url
    assert "repo" not in url.split("scope=")[1].split("&")[0]


@override_settings(**GITHUB_ON)
def test_github_callback_rejects_forged_state(api_client, db, monkeypatch):
    def fail(*a, **kw):
        raise AssertionError("must not exchange the code")

    monkeypatch.setattr("resume_renderer.views.requests.post", fail)
    api_client.get("/api/resume-renderer/github/connect/")

    resp = api_client.get(
        "/api/resume-renderer/github/callback/", {"code": "c", "state": "attacker"}
    )

    assert resp.status_code == 400
    assert "github_access_token" not in api_client.session


@override_settings(**GITHUB_ON)
def test_github_callback_handles_github_errors(api_client, db, monkeypatch):
    monkeypatch.setattr(
        "resume_renderer.views.requests.post", lambda *a, **kw: _Resp(500, {})
    )
    api_client.get("/api/resume-renderer/github/connect/")
    state = api_client.session["github_oauth_state"]

    resp = api_client.get(
        "/api/resume-renderer/github/callback/", {"code": "c", "state": state}
    )

    assert resp.status_code == 502


# --- 2.1: line-fitter jobs shared one directory in the container --------------


class _FakeContainer:
    def __init__(self):
        self.archive_paths = []
        self.workdirs = []
        self.commands = []

    def put_archive(self, path, data):
        self.archive_paths.append(path)

    def exec_run(self, cmd, workdir=None):
        self.commands.append(cmd)
        if workdir:
            self.workdirs.append(workdir)
        return 0, b"W:250.0pt\n"


def test_line_fitter_uses_unique_workdir_and_cleans_up(monkeypatch):
    container = _FakeContainer()
    monkeypatch.setattr(renderer, "_get_latex_container", lambda: container)

    assert line_fitter._measure_via_container(["one"]) == [250.0]
    line_fitter._measure_via_container(["two"])

    first, second = container.archive_paths
    assert first != second
    assert first.startswith("/usr/src/tex/measure-")
    assert container.workdirs == [first, second]
    assert ["rm", "-rf", first] in container.commands
    assert ["rm", "-rf", second] in container.commands
