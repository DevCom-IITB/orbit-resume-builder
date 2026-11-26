import logging
from typing import Dict, Any
from jsonschema import validate, ValidationError

from .llm_client import GeminiLLMClient
from .github_services import get_authenticated_repos, get_readme

logger = logging.getLogger(__name__)

KEY_PROJECT_SCHEMA: Dict[str, Any] = {
    "type": "array",
    "items": {
        "type": "object",
        "required": ["title", "organization", "readme", "language", "generation"],
        "additionalProperties": False,
        "properties": {
            "title": {"type": "string"},
            "organization": {"type": "string"},
            "readme": {"type": "string"},
            "language": {"type": "string"},
            # "bullets": {
            #     "type": "array",
            #     "items": {"type": "string"},
            # },
            "generation": {"type":"boolean"}
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

    # def extract_projects(self, username: str, max_repos: int = 5) -> list[dict]:
    #     """
    #     Fetches a user's GitHub repos + READMEs and extracts resume-ready
    #     project details matching KEY_PROJECT_SCHEMA.
    #     """
    #     try:
    #         # Using the imported service function
    #         repos = get_user_repos(username, max_repos=max_repos)
    #     except Exception as error:
    #         raise ProjectExtractionError(f"Failed to fetch repos for '{username}': {str(error)}")

    #     logger.info(f"Fetched {len(repos)} repos for '{username}'")

    #     projects = []
    #     for repo in repos:
    #         # Using the imported service function
    #         readme = get_readme(username, repo["name"])
    #         if not readme:
    #             logger.warning(f"No README for {username}/{repo['name']}, skipping")
    #             continue

    #         try:
    #             project = self._extract_single_project(repo, readme)
    #         except LLMClientError as e:
    #             # skip repos where the LLM call/parsing fails, don't fail the whole batch
    #             logger.warning(f"LLM extraction failed for {username}/{repo['name']}: {e}")
    #             continue

    #         if project is None:
    #             logger.warning(f"LLM returned no usable project for {username}/{repo['name']}")
    #             continue

    #         if self._is_valid(project):
    #             projects.append(project)
    #         else:
    #             logger.warning(
    #                 f"Schema validation failed for {username}/{repo['name']}: {project}"
    #             )

    #     return projects


    # ---------- Getting a list of repositories ----------
    def get_repositories(self, access_token: str, max_repos: int=10) -> list[dict]:
        """
            Fetch authenticated user's Github Repositories
        """

        try:
            return get_authenticated_repos(access_token=access_token,max_repos=max_repos)
        except Exception as error:
            raise ProjectExtractionError(f"Failed to fetch Github repos: {str(error)}")



    def import_projects(self, access_token: str, repositories: list[dict]) -> list[dict]:

        """
            Extract the projects from the repos
        """

        # Projects is when we were using the gemini client for the project extraction
        projects = []

        for repo in repositories:
            repo_name = repo.get("name")

            owner_data = repo.get("owner") or {}
            owner = owner_data.get("login")

            if not owner:
                full_name = repo.get("full_name", "")
                owner = (full_name.split("/", 1)[0] if "/" in full_name else None)

            if not owner or not repo_name:
                logger.warning("Skipping any repos with missing owner/name: %s", repo,)
                continue

            readme = get_readme(
                owner=owner,
                repo_name=repo_name,
                access_token=access_token
            )

            if not readme:
                logger.warning(f"No README for {owner}/{repo_name}, skipping")
                continue

            # Project extraction using GEMINI client
            try:
                project = {
                    "title": repo_name,
                    "organization": "",
                    "readme": readme,
                    "language": repo.get("language"),
                    "generation": False
                }

            except Exception as error:
                logger.warning("LLM extraction failed for %s/%s: %s", owner, repo_name, error)
                continue

            if project is None:
                logger.warning(f"LLM returned no usable project for {owner}, {repo_name}")
                continue

            if self._is_valid(project=project):
                projects.append(project)
                print('hi')
            else:
                logger.warning(f"Project is not valid, {owner}, {repo_name}: {project}")    

        return projects
        
    # ---------- LLM extraction ----------
    # Going to be removed in the next commit mostly
    def _extract_single_project(self, repo: dict, readme: str) -> dict | None:
        prompt = self._build_prompt(repo, readme)

        response_schema = {
            "type": "OBJECT",
            "properties": {
                "title": {
                    "type": "STRING",
                },
                "organization": {
                    "type": "STRING",
                },
                "summary": {
                    "type": "STRING",
                },
                "timeline": {
                    "type": "STRING",
                },
                "bullets": {
                    "type": "ARRAY",
                    "items": {
                        "type": "STRING",
                    },
                },
            },
            "required": [
                "title",
                "organization",
                "summary",
                "timeline",
                "bullets",
            ],
        }

        result = self.llm.generate_json(
            prompt,
            response_schema=response_schema,
        )

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
        allowed_keys = {"title", "organization", "readme", "language", "generation"}
        # Gemini often adds stray keys (e.g. "confidence") even when told not to.
        # Strip them in place so a harmless extra field doesn't nuke the whole project.
        for key in list(project.keys()):
            if key not in allowed_keys:
                project.pop(key)

        try:
            validate(instance=[project], schema=KEY_PROJECT_SCHEMA)
            return True
        except ValidationError as e:
            logger.warning(f"Validation error: {e.message}")
            return False