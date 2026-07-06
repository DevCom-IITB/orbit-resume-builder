import base64
import os
import requests

from jsonschema import validate, ValidationError

from .llm_client import GeminiLLMClient, LLMClientError


KEY_PROJECT_SCHEMA: Dict[str, Any] = {
    "type": "array",
    "items": {
        "type": "object",
        "required": ["title", "organization", "summary", "timeline", "bullets"],
        "additionalProperties": False,
        "properties": {
            "title": {"type": "string"},
            "organization": {"type": "string"},
            "summary": {"type": "string"},
            "timeline": {"type": "string"},
            "bullets": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
    },
}


GITHUB_API = "https://api.github.com"


class ProjectExtractionError(Exception):
    """Custom error for project extraction failures."""

    pass


class ProjectExtractionService:
    def __init__(self, llm_client: GeminiLLMClient = None):
        self.llm = llm_client or GeminiLLMClient()
        self.github_token = os.getenv("GITHUB_TOKEN")

    # ---------- Public API ----------

    def extract_projects(self, username: str, max_repos: int = 5) -> list[dict]:
        """
        Fetches a user's GitHub repos + READMEs and extracts resume-ready
        project details matching KEY_PROJECT_SCHEMA.
        """
        repos = self._get_user_repos(username, max_repos=max_repos)

        projects = []
        for repo in repos:
            readme = self._get_readme(username, repo["name"])
            if not readme:
                continue

            try:
                project = self._extract_single_project(repo, readme)
            except LLMClientError:
                # skip repos where the LLM call/parsing fails, don't fail the whole batch
                continue

            if project and self._is_valid(project):
                projects.append(project)

        return projects

    # ---------- GitHub fetching ----------

    def _github_headers(self) -> dict:
        headers = {"Accept": "application/vnd.github+json"}
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"
        return headers

    def _get_user_repos(self, username: str, max_repos: int) -> list[dict]:
        try:
            resp = requests.get(
                f"{GITHUB_API}/users/{username}/repos",
                params={"sort": "updated", "per_page": max_repos},
                headers=self._github_headers(),
                timeout=10,
            )
            resp.raise_for_status()
        except requests.RequestException as error:
            raise ProjectExtractionError(f"Failed to fetch repos for '{username}': {str(error)}")

        repos = resp.json()
        return [r for r in repos if not r.get("fork")]

    def _get_readme(self, owner: str, repo: str) -> str | None:
        resp = requests.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/readme",
            headers=self._github_headers(),
            timeout=10,
        )
        if resp.status_code != 200:
            return None

        content = resp.json().get("content", "")
        try:
            return base64.b64decode(content).decode("utf-8", errors="ignore")
        except Exception:
            return None

    # ---------- LLM extraction ----------

    def _extract_single_project(self, repo: dict, readme: str) -> dict | None:
        prompt = self._build_prompt(repo, readme)
        result = self.llm.generate_json(prompt)

        # Gemini might return a single object or a one-item list depending on prompt phrasing
        if isinstance(result, list):
            result = result[0] if result else None

        return result

    @staticmethod
    def _build_prompt(repo: dict, readme: str) -> str:
        return f"""You are extracting resume-ready project details from a GitHub README.

Given the repository metadata and README content below, return a single JSON object
(not wrapped in an array) matching exactly this schema:

{{
  "title": "short project name",
  "organization": "personal project / company name if mentioned, else 'Personal Project'",
  "summary": "1-2 sentence description of what the project does",
  "timeline": "date range if inferable from README/commits, else empty string",
  "bullets": ["resume-style bullet point highlighting impact/tech", "..."]
}}

Rules:
- Return ONLY the JSON object. No markdown fences, no preamble, no explanation.
- bullets should be 2-4 concise, achievement-oriented strings referencing tech stack, scale, or impact.
- If information is missing, infer reasonably from context, or use an empty string / empty array.

Repository: {repo.get('name', '')}
Description: {repo.get('description') or ''}
Language: {repo.get('language') or ''}
Stars: {repo.get('stargazers_count', 0)}

README:
{readme[:6000]}
"""

    # ---------- Validation ----------

    @staticmethod
    def _is_valid(project: dict) -> bool:
        try:
            validate(instance=[project], schema=KEY_PROJECT_SCHEMA)
            return True
        except ValidationError:
            return False