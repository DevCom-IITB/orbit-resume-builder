from django.http import HttpResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ParseError

from .schemas.config import RenderConfig
from .schemas.converters.convert_education import convert_education
from .schemas.converters.convert_experience import convert_experience
from .schemas.converters.convert_header import convert_header
from .schemas.converters.convert_key_project import convert_key_project
from .serializers import LatexRenderSerializer
from .services import renderer
from rest_framework.permissions import IsAuthenticated


class LatexRenderView(APIView):
    """Render resume data into a PDF."""

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
        config_data = data.get("config", {})

        serializer = LatexRenderSerializer(
            data={
                "header": header,
                "education": education,
                "experience": experience,
                "key_projects": key_projects,
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
            latex = "\n".join(
                [header_latex, education_latex, experience_latex, key_projects_latex]
            )
            pdf_bytes = renderer.compile_latex(latex)
        except RuntimeError as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return HttpResponse(pdf_bytes, content_type="application/pdf")
