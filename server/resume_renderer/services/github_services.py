# utils/github_fetcher.py
import base64
import requests
from django.conf import settings

GITHUB_API = "https://api.github.com"

def get_user_repos(username: str, max_repos: int = 10):
    headers = {"Accept": "application/vnd.github+json"}
    if getattr(settings, "GITHUB_TOKEN", None):
        headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"

    resp = requests.get(
        f"{GITHUB_API}/users/{username}/repos",
        params={"sort": "updated", "per_page": max_repos},
        headers=headers,
        timeout=10,
    )
    resp.raise_for_status()
    repos = resp.json()
    # filter out forks
    return [r for r in repos if not r.get("fork")]


def get_readme(owner: str, repo: str) -> str | None:
    headers = {"Accept": "application/vnd.github+json"}
    if getattr(settings, "GITHUB_TOKEN", None):
        headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"

    resp = requests.get(
        f"{GITHUB_API}/repos/{owner}/{repo}/readme",
        headers=headers,
        timeout=10,
    )
    if resp.status_code != 200:
        return None

    content = resp.json().get("content", "")
    try:
        return base64.b64decode(content).decode("utf-8", errors="ignore")
    except Exception:
        return None