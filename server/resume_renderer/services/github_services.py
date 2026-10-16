# utils/github_fetcher.py
import base64
import requests

GITHUB_API = "https://api.github.com"

def get_authenticated_repos(access_token: str, max_repos: int = 10):
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {access_token}",
    }

    resp = requests.get(
        f"{GITHUB_API}/user/repos",
        params={
            "sort": "updated",
            "per_page": max_repos,
        },
        headers=headers,
        timeout=10,
    )

    resp.raise_for_status()
    repos = resp.json()
    # filter out forks
    return [r for r in repos if not r.get("fork")]


def get_readme(owner: str, repo_name: str, access_token: str,) -> str | None:
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {access_token}",
    }

    resp = requests.get(
        f"{GITHUB_API}/repos/{owner}/{repo_name}/readme",
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