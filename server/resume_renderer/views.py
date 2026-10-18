import base64

import base64
import json
import traceback

from django.http import HttpResponse

from django.http import JsonResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ParseError
from rest_framework.decorators import api_view

from .services.project_extraction import ProjectExtractionService, ProjectExtractionError
from .schemas.config import RenderConfig
from .schemas.converters.convert_education import convert_education
from .schemas.converters.convert_experience import convert_experience
from .schemas.converters.convert_header import convert_header
from .schemas.converters.convert_key_project import convert_key_project
from .schemas.converters.convert_pors import convert_pors
from .schemas.converters.convert_scholastic_achievements import (
    convert_scholastic_achievements,
)
from .schemas.converters.convert_courses import convert_courses
from .schemas.converters.convert_technical_skills import convert_technical_skills
from .serializers import LatexRenderSerializer
from .services import renderer
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from utils.token_dec import token_required

import jsonschema
from resume_renderer.JSONSchema.jsonschema import (
    get_schema,
    get_supported_section_types,
)
from resume_renderer.serializers import ResumeSectionRefineSerializer
from resume_renderer.services.llm_client import GeminiLLMClient ,LLMClient, LLMClientError
from resume_renderer.services.llm_rate_limiter import rate_limiter
from resume_renderer.services.prompts import build_resume_prompt
from resume_renderer.services.security import (
    check_user_restriction,
    detect_prompt_injection,
    get_client_ip,
    log_security_event,
    record_user_violation,
    validate_and_classify_llm_output,
)

import requests
from django.conf import settings

from urllib.parse import urlencode

@method_decorator(csrf_exempt, name="dispatch")
class LatexRenderView(APIView):
    """Render resume data into a PDF."""

    @token_required
    def post(self, request):
        try:
            data = request.data
        except ParseError:
            return Response(
                {"error": "Invalid JSON payload."}, status=status.HTTP_400_BAD_REQUEST
            )

        if not isinstance(data, dict):
            return Response(
                {"error": "JSON payload must be an object."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        header = data.get("header", {})
        if not header or "name" not in header:
            user = request.user if hasattr(request, "user") and request.user else None
            username = user.username if user else "Student"
            first_name = user.first_name if user else ""
            last_name = user.last_name if user else ""
            email = user.email if user else f"{username}@iitb.ac.in"
            
            full_name = f"{first_name} {last_name}".strip() or username
            header = {
                "name": full_name,
                "edu": "B.Tech. in Computer Science & Engineering",
                "contact": {
                    "email": email,
                    "phone": "+91 99999 99999",
                    "linkedin": username.lower(),
                    "github": username.lower(),
                },
            }

        education = data.get("education", [])
        experience = data.get("experience", [])
        key_projects = data.get("key_projects", [])
        pors = data.get("pors", [])
        scholastic_achievements = data.get("scholastic_achievements", [])
        courses = data.get("courses", [])
        technical_skills = data.get("technical_skills", [])
        config_data = data.get("config", {})

        serializer = LatexRenderSerializer(
            data={
                "header": header,
                "education": education,
                "experience": experience,
                "key_projects": key_projects,
                "pors": pors,
                "scholastic_achievements": scholastic_achievements,
                "courses": courses,
                "technical_skills": technical_skills,
                "config": config_data,
            }
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        if not isinstance(config_data, dict):
            return Response(
                {"error": "config must be an object."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        config = RenderConfig(**config_data)

        try:
            header_latex = convert_header(header) if config.use_header else ""
            education_latex = convert_education(education)
            experience_latex = convert_experience(experience)
            key_projects_latex = convert_key_project(key_projects)
            pors_latex = convert_pors(pors)
            scholastic_latex = convert_scholastic_achievements(scholastic_achievements)
            courses_latex = convert_courses(courses)
            technical_latex = convert_technical_skills(technical_skills)
            latex = "\n".join(
                [
                    header_latex,
                    education_latex,
                    experience_latex,
                    key_projects_latex,
                    pors_latex,
                    scholastic_latex,
                    courses_latex,
                    technical_latex,
                ]
            )
            pdf_bytes = renderer.compile_latex(latex)
        except RuntimeError as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return JsonResponse(
            {
                "latex": latex,
                "pdf": base64.b64encode(pdf_bytes).decode("utf-8"),
            }
        )


@api_view(["POST"])
def refine_resume_section(request, section_type):
    """
    Refine rough user input into resume-ready JSON using the LLM.

    URL:
        POST /api/resume-renderer/<section_type>/

    Example:
        POST /api/resume-renderer/professional_experience/

    Expected request body:
    {
        "user_input": "worked as frontend intern at Awaasdhan..."
    }

    Response:
    {
        "success": true,
        "section_type": "professional_experience",
        "data": [...]
    }
    """

    supported_sections = get_supported_section_types()

    if section_type not in supported_sections:
        return Response(
            {
                "success": False,
                "error": "Unsupported section type.",
                "section_type": section_type,
                "supported_section_types": supported_sections,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    serializer = ResumeSectionRefineSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(
            {
                "success": False,
                "errors": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    user_input = serializer.validated_data["user_input"]
    ldap_id = getattr(request.user, "username", "anonymous")
    ip_address = get_client_ip(request)

    # 1. Check account restriction
    restriction = check_user_restriction(ldap_id)
    if restriction is not None:
        blocked_str = restriction.blocked_until.isoformat() if restriction.blocked_until else ""
        return Response(
            {
                "success": False,
                "error": "account_restricted",
                "message": "AI generation is temporarily restricted for this account.",
                "blocked_until": blocked_str,
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    # 2. Check prompt injection signal
    if detect_prompt_injection(user_input):
        record_user_violation(
            ldap_id=ldap_id,
            event_type="PROMPT_INJECTION_SIGNAL",
            severity="high",
            section_type=section_type,
            endpoint=request.path,
            ip_address=ip_address,
            metadata={"input_snippet": user_input[:200]},
        )

    # 3. Rate limiting check & acquire
    rate_res = rate_limiter.check_and_acquire(ldap_id)
    if not rate_res.is_allowed:
        ev_type = (
            "LLM_DAILY_LIMIT_EXCEEDED"
            if rate_res.limit_type == "daily"
            else "LLM_RATE_LIMIT_EXCEEDED"
        )
        log_security_event(
            ldap_id=ldap_id,
            event_type=ev_type,
            severity="warning",
            section_type=section_type,
            endpoint=request.path,
            ip_address=ip_address,
            metadata={
                "limit_type": rate_res.limit_type,
                "retry_after": rate_res.retry_after,
                "current_count": rate_res.current_count,
            },
        )
        return Response(
            {
                "success": False,
                "error": "llm_rate_limit_exceeded",
                "limit_type": rate_res.limit_type,
                "message": rate_res.message,
                "retry_after": rate_res.retry_after,
                "reset_at": rate_res.reset_at.isoformat() if rate_res.reset_at else None,
            },
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    try:
        prompt = build_resume_prompt(section_type, user_input)

        llm_client = GeminiLLMClient()
        llm_output = llm_client.generate_json(prompt)

        schema = get_schema(section_type)
        is_valid, is_empty, err_msg = validate_and_classify_llm_output(
            llm_output, schema, section_type
        )

        if not is_valid:
            log_security_event(
                ldap_id=ldap_id,
                event_type="INVALID_LLM_JSON",
                severity="warning",
                section_type=section_type,
                endpoint=request.path,
                ip_address=ip_address,
                metadata={"error": err_msg},
            )
            return Response(
                {
                    "success": False,
                    "error": "invalid_llm_json",
                    "details": err_msg,
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if is_empty:
            record_user_violation(
                ldap_id=ldap_id,
                event_type="OFF_TOPIC_INPUT",
                severity="info",
                section_type=section_type,
                endpoint=request.path,
                ip_address=ip_address,
                metadata={"input_snippet": user_input[:200]},
            )
            return Response(
                {
                    "success": False,
                    "error": "invalid_resume_content",
                    "message": "The input does not appear to contain content relevant to this resume section.",
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        return Response(
            {
                "success": True,
                "section_type": section_type,
                "data": llm_output,
            },
            status=status.HTTP_200_OK,
        )

    except LLMClientError as error:
        log_security_event(
            ldap_id=ldap_id,
            event_type="LLM_PROVIDER_ERROR",
            severity="warning",
            section_type=section_type,
            endpoint=request.path,
            ip_address=ip_address,
            metadata={"error": str(error)},
        )
        return Response(
            {
                "success": False,
                "error": "llm_provider_error",
                "message": "The AI service could not complete this request. Please try again later.",
                "details": str(error),
            },
            status=status.HTTP_502_BAD_GATEWAY,
        )

    except Exception as error:
        return Response(
            {
                "success": False,
                "error": "Unexpected server error.",
                "details": str(error),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class GitHubConnectAPIView(APIView):
    """
    Returns the GitHub OAuth authorization URL.
    """

    def get(self, request):
        redirect_to = request.query_params.get(
            "redirect_to",
            "/",
        )

        state = base64.urlsafe_b64encode(
            json.dumps(
                {
                    "redirect_to": redirect_to,
                }
            ).encode()
        ).decode()

        params = {
            "client_id": settings.GITHUB_CLIENT_ID,
            "redirect_uri": settings.GITHUB_REDIRECT_URI,
            "scope": "repo read:user",
            "state": state,
        }

        query = urlencode(params)

        return Response(
            {
                "authorization_url":
                    f"https://github.com/login/oauth/authorize?{query}"
            }
        )

class GitHubCallbackAPIView(APIView):
    """
    Exchanges GitHub OAuth code for an access token.
    """

    def get(self, request):
        code = request.query_params.get("code")
        state = request.query_params.get("state")

        if not code:
            return Response(
                {"error": "Missing authorization code."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        response = requests.post(
            "https://github.com/login/oauth/access_token",
            headers={
                "Accept": "application/json",
            },
            data={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": settings.GITHUB_REDIRECT_URI,
            },
            timeout=10,
        )

        response.raise_for_status()

        token = response.json().get("access_token")

        if token is None:
            return Response(
                {"error": "Failed to obtain access token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        request.session["github_access_token"] = token
        request.session.modified = True

        if state:
            try:
                decoded_state = json.loads(
                    base64.urlsafe_b64decode(state).decode()
                )
            except Exception:
                pass

        return HttpResponse(
            f"""
            <!DOCTYPE html>
            <html>
                <head>
                    <title>GitHub Authentication</title>
                </head>

                <body>
                    <script>
                        window.close();
                    </script>
                </body>
            </html>
            """
        )
    
class GitHubStatusAPIView(APIView):
    """
    Returns whether the current user has connected GitHub.
    """

    def get(self, request):
        connected = "github_access_token" in request.session

        return Response(
            {
                "connected": connected
            }
        )
       
class GitHubRepositoriesAPIView(APIView):
    """
    Returns the authenticated user's GitHub repositories.
    """

    def get(self, request, *args, **kwargs):
        max_repos = int(request.query_params.get("max_repos", 10))

        token = request.session.get("github_access_token")

        if token is None:
            return Response(
                {
                    "success": False,
                    "error": "GitHub account not connected."
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            service = ProjectExtractionService()

            repositories = service.get_repositories(
                access_token=token,
                max_repos=max_repos,
            )

            return Response(
                {
                    "success": True,
                    "data": repositories,
                },
                status=status.HTTP_200_OK,
            )

        except ProjectExtractionError as error:
            return Response(
                {
                    "success": False,
                    "error": str(error),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as error:
            traceback.print_exc()

            return Response(
                {
                    "success": False,
                    "error": str(error),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        
class GitHubImportProjectsAPIView(APIView):
    """
    Extracts resume-ready projects from the selected repositories.
    """

    def post(self, request, *args, **kwargs):
        token = request.session.get("github_access_token")

        if token is None:
            return Response(
                {
                    "success": False,
                    "error": "GitHub account not connected."
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        repositories = request.data.get("repositories", [])

        try:
            service = ProjectExtractionService()

            projects = service.import_projects(
                access_token=token,
                repositories=repositories,
            )

            return Response(
                {
                    "success": True,
                    "data": projects,
                },
                status=status.HTTP_200_OK,
            )

        except ProjectExtractionError as error:
            return Response(
                {
                    "success": False,
                    "error": str(error),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except Exception as error:
            traceback.print_exc()

            return Response(
                {
                    "success": False,
                    "error": str(error),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )