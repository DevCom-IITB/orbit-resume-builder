import base64

import jsonschema as jsonschema_lib
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from resume_renderer.services.line_fitter import fit_bullets_in_content
from resume_renderer.services.llm_client import LLMClient, LLMClientError
from resume_renderer.services.prompts import build_resume_prompt
from resume_renderer.services.renderer import assemble_resume_latex, compile_latex
from utils.token_dec import token_required

from .models import Resume, ResumeTemplate, Section, SectionEntry, TemplateSectionType, Version, VisualTheme
from .serializers import (
    ResumeCreateSerializer,
    ResumeDetailSerializer,
    ResumeListSerializer,
    ResumePatchSerializer,
    ResumeTemplateSerializer,
    SectionEntrySerializer,
    SectionSerializer,
    VersionSerializer,
    VisualThemeSerializer,
)


def _get_resume_or_404(resume_id, user):
    try:
        return Resume.objects.select_related("template", "visual_theme").get(
            id=resume_id, owner=user
        )
    except Resume.DoesNotExist:
        return None


def _get_section_or_404(resume, section_id):
    try:
        return resume.sections.select_related("section_type").get(id=section_id)
    except Section.DoesNotExist:
        return None


def _get_entry_or_404(section, entry_id):
    try:
        return section.entries.get(id=entry_id)
    except SectionEntry.DoesNotExist:
        return None


@method_decorator(csrf_exempt, name="dispatch")
class TemplateListView(APIView):
    @token_required
    def get(self, request):
        templates = ResumeTemplate.objects.filter(is_active=True).prefetch_related("available_themes")
        return Response(ResumeTemplateSerializer(templates, many=True).data)


@method_decorator(csrf_exempt, name="dispatch")
class VisualThemeListView(APIView):
    @token_required
    def get(self, request):
        qs = VisualTheme.objects.all()
        family = request.GET.get("family")
        if family:
            qs = qs.filter(compatible_families__contains=family)
        return Response(VisualThemeSerializer(qs, many=True).data)


@method_decorator(csrf_exempt, name="dispatch")
class ResumeListCreate(APIView):
    @token_required
    def get(self, request):
        resumes = Resume.objects.filter(owner=request.user).select_related(
            "template", "visual_theme"
        ).order_by("-is_pinned", "-updated_at")
        return Response({
            "count": resumes.count(),
            "results": ResumeListSerializer(resumes, many=True).data,
        })

    @token_required
    def post(self, request):
        serializer = ResumeCreateSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            resume = serializer.save()
            return Response(
                ResumeDetailSerializer(resume).data,
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name="dispatch")
class ResumeDetail(APIView):
    @token_required
    def get(self, request, resume_id):
        resume = _get_resume_or_404(resume_id, request.user)
        if not resume:
            return Response({"error": "not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(ResumeDetailSerializer(resume).data)

    @token_required
    def patch(self, request, resume_id):
        resume = _get_resume_or_404(resume_id, request.user)
        if not resume:
            return Response({"error": "not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = ResumePatchSerializer(resume, data=request.data, partial=True)
        if serializer.is_valid():
            updated = serializer.save()
            Version.objects.create(
                resume=updated,
                snapshot=ResumeDetailSerializer(updated).data,
                created_by=request.user,
            )
            return Response(ResumeDetailSerializer(updated).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @token_required
    def delete(self, request, resume_id):
        resume = _get_resume_or_404(resume_id, request.user)
        if not resume:
            return Response({"error": "not found"}, status=status.HTTP_404_NOT_FOUND)
        resume.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator(csrf_exempt, name="dispatch")
class ResumeDuplicate(APIView):
    @token_required
    def post(self, request, resume_id):
        source = _get_resume_or_404(resume_id, request.user)
        if not source:
            return Response({"error": "not found"}, status=status.HTTP_404_NOT_FOUND)

        new_resume = Resume.objects.create(
            owner=request.user,
            title=f"{source.title} (Copy)",
            template=source.template,
            visual_theme=source.visual_theme,
            pages=source.pages,
            config_override=source.config_override,
            is_pinned=False,
        )
        for section in source.sections.select_related("section_type").all():
            new_section = Section.objects.create(
                resume=new_resume,
                section_type=section.section_type,
                order=section.order,
                is_visible=section.is_visible,
            )
            for entry in section.entries.all():
                SectionEntry.objects.create(
                    section=new_section,
                    order=entry.order,
                    raw_input=entry.raw_input,
                    content=entry.content,
                    generation_status=entry.generation_status,
                )

        return Response(
            ResumeDetailSerializer(new_resume).data,
            status=status.HTTP_201_CREATED,
        )


@method_decorator(csrf_exempt, name="dispatch")
class RenderResumeView(APIView):
    @token_required
    def post(self, request, resume_id):
        resume = _get_resume_or_404(resume_id, request.user)
        if not resume:
            return Response({"error": "not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            latex = assemble_resume_latex(resume)
            pdf_bytes = compile_latex(latex)
            pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")
            return Response({"pdf": pdf_b64, "latex": latex})
        except Exception as exc:
            return Response({"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name="dispatch")
class SectionListCreate(APIView):
    @token_required
    def get(self, request, resume_id):
        resume = _get_resume_or_404(resume_id, request.user)
        if not resume:
            return Response({"error": "not found"}, status=status.HTTP_404_NOT_FOUND)
        sections = resume.sections.select_related("section_type").prefetch_related("entries")
        return Response(SectionSerializer(sections, many=True).data)

    @token_required
    def post(self, request, resume_id):
        resume = _get_resume_or_404(resume_id, request.user)
        if not resume:
            return Response({"error": "not found"}, status=status.HTTP_404_NOT_FOUND)

        section_type_key = request.data.get("section_type_key")
        if not section_type_key:
            return Response(
                {"error": "section_type_key is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate this section type exists in the template's manifest
        tst = TemplateSectionType.objects.filter(
            template=resume.template, section_type__key=section_type_key
        ).select_related("section_type").first()

        if not tst:
            return Response(
                {"error": f"Section type '{section_type_key}' is not available for this template."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Enforce unique_together — section type already on this resume
        if resume.sections.filter(section_type=tst.section_type).exists():
            return Response(
                {"error": f"Section '{section_type_key}' already exists on this resume."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        max_order = resume.sections.order_by("-order").values_list("order", flat=True).first()
        new_order = (max_order or 0) + 1

        section = Section.objects.create(
            resume=resume,
            section_type=tst.section_type,
            order=new_order,
            is_visible=True,
        )
        # Create empty entry for singleton sections
        if not tst.section_type.allow_multiple_entries:
            SectionEntry.objects.create(
                section=section, order=0, raw_input="", content=None, generation_status="pending"
            )

        return Response(SectionSerializer(section).data, status=status.HTTP_201_CREATED)


@method_decorator(csrf_exempt, name="dispatch")
class SectionDetail(APIView):
    @token_required
    def patch(self, request, resume_id, section_id):
        resume = _get_resume_or_404(resume_id, request.user)
        if not resume:
            return Response({"error": "not found"}, status=status.HTTP_404_NOT_FOUND)
        section = _get_section_or_404(resume, section_id)
        if not section:
            return Response({"error": "not found"}, status=status.HTTP_404_NOT_FOUND)

        if "order" in request.data:
            section.order = int(request.data["order"])
        if "is_visible" in request.data:
            section.is_visible = bool(request.data["is_visible"])
            resume.latex_cache_valid = False
            resume.save(update_fields=["latex_cache_valid"])
        section.save()
        return Response(SectionSerializer(section).data)

    @token_required
    def delete(self, request, resume_id, section_id):
        resume = _get_resume_or_404(resume_id, request.user)
        if not resume:
            return Response({"error": "not found"}, status=status.HTTP_404_NOT_FOUND)
        section = _get_section_or_404(resume, section_id)
        if not section:
            return Response({"error": "not found"}, status=status.HTTP_404_NOT_FOUND)

        tst = TemplateSectionType.objects.filter(
            template=resume.template, section_type=section.section_type
        ).first()
        if tst and tst.is_required:
            return Response(
                {"error": f"Section '{section.section_type.key}' is required and cannot be removed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        section.delete()
        resume.latex_cache_valid = False
        resume.save(update_fields=["latex_cache_valid"])
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator(csrf_exempt, name="dispatch")
class EntryListCreate(APIView):
    @token_required
    def post(self, request, resume_id, section_id):
        resume = _get_resume_or_404(resume_id, request.user)
        if not resume:
            return Response({"error": "not found"}, status=status.HTTP_404_NOT_FOUND)
        section = _get_section_or_404(resume, section_id)
        if not section:
            return Response({"error": "not found"}, status=status.HTTP_404_NOT_FOUND)

        if not section.section_type.allow_multiple_entries:
            return Response(
                {"error": "This section only supports a single entry."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        max_order = section.entries.order_by("-order").values_list("order", flat=True).first()
        new_order = (max_order or -1) + 1

        entry = SectionEntry.objects.create(
            section=section,
            order=new_order,
            raw_input=request.data.get("raw_input", ""),
            content=None,
            generation_status="pending",
        )
        return Response(SectionEntrySerializer(entry).data, status=status.HTTP_201_CREATED)


@method_decorator(csrf_exempt, name="dispatch")
class EntryDetail(APIView):
    @token_required
    def patch(self, request, resume_id, section_id, entry_id):
        resume = _get_resume_or_404(resume_id, request.user)
        if not resume:
            return Response({"error": "not found"}, status=status.HTTP_404_NOT_FOUND)
        section = _get_section_or_404(resume, section_id)
        if not section:
            return Response({"error": "not found"}, status=status.HTTP_404_NOT_FOUND)
        entry = _get_entry_or_404(section, entry_id)
        if not entry:
            return Response({"error": "not found"}, status=status.HTTP_404_NOT_FOUND)

        if "raw_input" in request.data:
            entry.raw_input = request.data["raw_input"]
        if "content" in request.data:
            entry.content = request.data["content"]
            resume.latex_cache_valid = False
            resume.save(update_fields=["latex_cache_valid"])
        if "order" in request.data:
            entry.order = int(request.data["order"])

        entry.save()
        return Response(SectionEntrySerializer(entry).data)

    @token_required
    def delete(self, request, resume_id, section_id, entry_id):
        resume = _get_resume_or_404(resume_id, request.user)
        if not resume:
            return Response({"error": "not found"}, status=status.HTTP_404_NOT_FOUND)
        section = _get_section_or_404(resume, section_id)
        if not section:
            return Response({"error": "not found"}, status=status.HTTP_404_NOT_FOUND)
        entry = _get_entry_or_404(section, entry_id)
        if not entry:
            return Response({"error": "not found"}, status=status.HTTP_404_NOT_FOUND)

        # Block deletion of singleton section's only entry
        if not section.section_type.allow_multiple_entries:
            return Response(
                {"error": "Cannot delete the entry of a singleton section."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        entry.delete()
        resume.latex_cache_valid = False
        resume.save(update_fields=["latex_cache_valid"])
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator(csrf_exempt, name="dispatch")
class GenerateEntryView(APIView):
    @token_required
    def post(self, request, resume_id, section_id, entry_id):
        resume = _get_resume_or_404(resume_id, request.user)
        if not resume:
            return Response({"error": "not found"}, status=status.HTTP_404_NOT_FOUND)
        section = _get_section_or_404(resume, section_id)
        if not section:
            return Response({"error": "not found"}, status=status.HTTP_404_NOT_FOUND)
        entry = _get_entry_or_404(section, entry_id)
        if not entry:
            return Response({"error": "not found"}, status=status.HTTP_404_NOT_FOUND)

        if not entry.raw_input.strip():
            return Response(
                {"error": "raw_input is empty — provide input before generating."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        stdef = section.section_type

        # Mark as generating
        entry.generation_status = "generating"
        entry.save(update_fields=["generation_status"])

        try:
            # Generate the query embedding from user's raw input
            from rag.utils import EmbeddingService
            query_embedding = None
            try:
                query_embedding = EmbeddingService().embed(entry.raw_input)
            except Exception as embed_exc:
                # Log or print warning, don't crash generation if embedding service fails
                print(f"[WARN] Local embedding generation failed: {embed_exc}")

            prompt = build_resume_prompt(
                section_type=stdef.key,
                user_input=entry.raw_input,
                current_content=entry.content,
                stdef=stdef,
                query_embedding=query_embedding,
            )
            entry.last_sent_prompt = prompt
            entry.save(update_fields=["last_sent_prompt"])

            llm = LLMClient()
            raw_output = llm.generate_json(prompt)

            # Validate against schema
            jsonschema_lib.validate(instance=raw_output, schema=stdef.json_schema)

            # Measure bullet widths and repair out-of-band ones (1 LLM retry).
            raw_output = fit_bullets_in_content(raw_output, stdef.key, llm)

            entry.content = raw_output
            entry.generation_status = "done"
            entry.save(update_fields=["content", "generation_status", "updated_at"])

            resume.latex_cache_valid = False
            resume.save(update_fields=["latex_cache_valid"])

            return Response(SectionEntrySerializer(entry).data)

        except LLMClientError as exc:
            entry.generation_status = "failed"
            entry.save(update_fields=["generation_status"])
            return Response({"error": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        except jsonschema_lib.ValidationError as exc:
            entry.generation_status = "failed"
            entry.save(update_fields=["generation_status"])
            return Response(
                {"error": f"LLM output failed schema validation: {exc.message}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception as exc:
            entry.generation_status = "failed"
            entry.save(update_fields=["generation_status"])
            return Response({"error": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
