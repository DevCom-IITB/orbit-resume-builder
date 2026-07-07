from typing import Dict, Any
from jsonschema import validate, ValidationError

from .llm_client import GeminiLLMClient, LLMClientError
from .github_services import (get_authenticated_repos, get_readme)
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

class ProjectExtractionError(Exception):
    """Custom error for project extraction failures."""
    pass

class ProjectExtractionService:
    def __init__(self, llm_client: GeminiLLMClient = None):
        self.llm = llm_client or GeminiLLMClient()
        # Removed self.github_token since github_services.py handles it via Django settings

    # ---------- Public API ----------

    def get_repositories(self, access_token: str, max_repos: int = 10) -> list[dict]:
        """
        Fetches a user's GitHub repos + READMEs and extracts resume-ready
        project details matching KEY_PROJECT_SCHEMA.
        """

        try:
            return get_authenticated_repos(
                access_token=access_token,
                max_repos=max_repos,
            )
        except Exception as error:
            raise ProjectExtractionError(
                f"Failed to fetch repositories: {str(error)}"
            )
        
    def import_projects(self, access_token: str, repositories: list[dict]) -> list[dict]:
        """
        Extract resume-ready projects only from the
        repositories selected by the user.
        """

        projects = []

        for repo in repositories:
            readme = get_readme(
                owner=repo["owner"]["login"],
                repo_name=repo["name"],
                access_token=access_token,
            )

            if not readme:
                continue

            try:
                project = self._extract_single_project(repo, readme)
            except LLMClientError:
                continue

            if project and self._is_valid(project):
                projects.append(project)

        return projects
    
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