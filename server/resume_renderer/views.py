import base64

from django.http import JsonResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ParseError
from rest_framework.decorators import api_view
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
from rest_framework.permissions import IsAuthenticated
from utils.token_dec import ReachTokenAuthentication

import jsonschema
from resume_renderer.JSONSchema.jsonschema import (
    get_schema,
    get_supported_section_types,
)
from resume_renderer.serializers import ResumeSectionRefineSerializer
from resume_renderer.services.llm_client import GeminiLLMClient, LLMClientError
from resume_renderer.services.prompts import build_resume_prompt


class LatexRenderView(APIView):
    """Render resume data into a PDF."""

    authentication_classes = [ReachTokenAuthentication]
    permission_classes = [IsAuthenticated]

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
            # The editor may not send a header at all; skip it rather than fail.
            header_latex = (
                convert_header(header) if config.use_header and header else ""
            )
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
        except ValueError as e:
            # Converters raise ValueError for missing keys / malformed entries.
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
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

    try:
        prompt = build_resume_prompt(section_type, user_input)

        llm_client = GeminiLLMClient()
        llm_output = llm_client.generate_json(prompt)

        schema = get_schema(section_type)
        jsonschema.validate(instance=llm_output, schema=schema)

        return Response(
            {
                "success": True,
                "section_type": section_type,
                "data": llm_output,
            },
            status=status.HTTP_200_OK,
        )

    except jsonschema.ValidationError as error:
        return Response(
            {
                "success": False,
                "error": "LLM output did not match the expected JSON schema.",
                "details": error.message,
            },
            status=status.HTTP_502_BAD_GATEWAY,
        )

    except LLMClientError as error:
        return Response(
            {
                "success": False,
                "error": "LLM generation failed.",
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
