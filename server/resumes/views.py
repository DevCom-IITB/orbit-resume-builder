import base64

import jsonschema as jsonschema_lib
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from resume_renderer.services.line_fitter import fit_bullets_in_content
from resume_renderer.services.llm_client import LLMClient, LLMClientError
from resume_renderer.services.llm_rate_limiter import rate_limiter
from resume_renderer.services.prompts import build_resume_prompt, build_resume_import_prompt
from resume_renderer.services.renderer import assemble_resume_latex, compile_latex
from resume_renderer.services.security import (
    check_user_restriction,
    detect_prompt_injection,
    get_client_ip,
    log_security_event,
    record_user_violation,
    validate_and_classify_llm_output,
)
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
from rag.retrieval.filtering import SectionKey


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
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        import_content = serializer.validated_data.get("import_content", "").strip()

        if import_content:
            ldap_id = getattr(request.user, "username", "unknown")
            ip_address = get_client_ip(request)

            # 1. Check account restriction
            restriction = check_user_restriction(ldap_id)
            if restriction is not None:
                blocked_str = restriction.blocked_until.isoformat() if restriction.blocked_until else ""
                return Response(
                    {
                        "error": "account_restricted",
                        "message": "AI generation is temporarily restricted for this account.",
                        "blocked_until": blocked_str,
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            # 2. Check prompt injection
            if detect_prompt_injection(import_content):
                record_user_violation(
                    ldap_id=ldap_id,
                    event_type="PROMPT_INJECTION_SIGNAL",
                    severity="high",
                    endpoint=request.path,
                    ip_address=ip_address,
                    metadata={"input_snippet": import_content[:200]},
                )
                return Response(
                    {
                        "error": "invalid_resume_content",
                        "message": "The input was flagged by security filters. Please check your content.",
                    },
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )

            # 3. Check rate limit
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
                    endpoint=request.path,
                    ip_address=ip_address,
                    metadata={
                        "limit_type": rate_res.limit_type,
                        "retry_after": rate_res.retry_after,
                        "current_count": rate_res.current_count,
                    },
                )
                print(
                    f"[LLM Rate Limit] User '{ldap_id}' rate limit exceeded ({rate_res.limit_type}): {rate_res.message}",
                    flush=True,
                )
                return Response(
                    {
                        "error": "llm_rate_limit_exceeded",
                        "limit_type": rate_res.limit_type,
                        "message": rate_res.message,
                        "retry_after": rate_res.retry_after,
                        "reset_at": rate_res.reset_at.isoformat() if rate_res.reset_at else None,
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )

            # 4. Generate structured JSON via LLM
            prompt = build_resume_import_prompt(import_content)
            try:
                llm = LLMClient()
                parsed_data = llm.generate_json(prompt)
                if not isinstance(parsed_data, dict):
                    parsed_data = {}
            except LLMClientError as exc:
                print(
                    f"[LLM Error] Resume import failed for user '{ldap_id}': {exc}",
                    flush=True,
                )
                log_security_event(
                    ldap_id=ldap_id,
                    event_type="LLM_PROVIDER_ERROR",
                    severity="warning",
                    endpoint=request.path,
                    ip_address=ip_address,
                    metadata={"error": str(exc)},
                )
                return Response(
                    {
                        "error": "llm_provider_error",
                        "message": f"Resume import failed: {str(exc)}",
                    },
                    status=status.HTTP_502_BAD_GATEWAY,
                )

            serializer.validated_data["_parsed_data"] = parsed_data

        resume = serializer.save()
        return Response(
            ResumeDetailSerializer(resume).data,
            status=status.HTTP_201_CREATED,
        )


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
        except ValueError as exc:
            ldap_id = getattr(request.user, "username", "unknown")
            ip_address = get_client_ip(request)
            record_user_violation(
                ldap_id=ldap_id,
                event_type="RENDERING_SECURITY_VIOLATION",
                severity="high",
                resume_id=str(resume.id),
                endpoint=request.path,
                ip_address=ip_address,
                metadata={"error": str(exc)},
            )
            return Response(
                {"error": f"Rendering security violation: {str(exc)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            return Response({"error": f"Resume compilation failed: {str(exc)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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

        stdef = section.section_type
        ldap_id = getattr(request.user, "username", "anonymous")
        ip_address = get_client_ip(request)

        # 1. Check account restriction in MySQL/Django
        restriction = check_user_restriction(ldap_id)
        if restriction is not None:
            blocked_str = restriction.blocked_until.isoformat() if restriction.blocked_until else ""
            return Response(
                {
                    "error": "account_restricted",
                    "message": "AI generation is temporarily restricted for this account.",
                    "blocked_until": blocked_str,
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # 2. Validate basic input constraints
        if not entry.raw_input or not entry.raw_input.strip():
            return Response(
                {"error": "raw_input is empty — provide input before generating."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 3. Check for prompt injection signal in untrusted user input
        if detect_prompt_injection(entry.raw_input):
            record_user_violation(
                ldap_id=ldap_id,
                event_type="PROMPT_INJECTION_SIGNAL",
                severity="high",
                resume_id=str(resume.id),
                section_type=stdef.key,
                endpoint=request.path,
                ip_address=ip_address,
                metadata={"input_snippet": entry.raw_input[:200]},
            )

        # 4. Check & acquire quota from Redis rate limiter (atomic Lua script)
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
                resume_id=str(resume.id),
                section_type=stdef.key,
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
                    "error": "llm_rate_limit_exceeded",
                    "limit_type": rate_res.limit_type,
                    "message": rate_res.message,
                    "retry_after": rate_res.retry_after,
                    "reset_at": rate_res.reset_at.isoformat() if rate_res.reset_at else None,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # Mark as generating
        entry.generation_status = "generating"
        entry.save(update_fields=["generation_status"])

        try:
            # Only these section types have a senior-resume retrieval repository.
            RETRIEVAL_SECTION_KEYS = {s.value for s in SectionKey}

            retrieved_context = None
            if stdef.key in RETRIEVAL_SECTION_KEYS:
                try:
                    from rag.chroma_client import get_resume_collection
                    from rag.retrieval.main_pipeline import run_retrieval_pipeline

                    collection = get_resume_collection()
                    rag_result = run_retrieval_pipeline(
                        query=entry.raw_input,
                        section_key=stdef.key,
                        chroma_collection=collection,
                        top_n=20,
                        top_m=5,
                    )
                    retrieved_context = rag_result.get("retrieved_context")
                    if retrieved_context:
                        print(f"\n==================== [RAG RETRIEVAL PIPELINE] ====================")
                        print(f"Query/Input: {repr(entry.raw_input[:100])}...")
                        print(f"Retrieved {len(retrieved_context)} context chunks for LLM Generation:")
                        for idx, ctx in enumerate(retrieved_context):
                            print(f"  * Chunk #{idx+1} | Score: {ctx.get('score')} | Section: {ctx.get('section_key')} | Title: {ctx.get('entry_title')}")
                            print(f"    Content: {repr(ctx.get('chunk')[:150])}...")
                        print(f"==================================================================\n")
                except Exception as rag_exc:
                    # Don't crash generation if retrieval fails — proceed without context.
                    print(f"[WARN] RAG retrieval failed: {rag_exc}")
                    retrieved_context = None

            prompt = build_resume_prompt(
                section_type=stdef.key,
                user_input=entry.raw_input,
                current_content=entry.content,
                stdef=stdef,
                retrieved_context=retrieved_context,
            )
            entry.last_sent_prompt = prompt
            entry.save(update_fields=["last_sent_prompt"])

            llm = LLMClient()
            raw_output = llm.generate_json(prompt)

            # 5. Validate output against expected JSON schema and classify content
            is_valid, is_empty, err_msg = validate_and_classify_llm_output(
                raw_output, stdef.json_schema, stdef.key
            )

            if not is_valid:
                log_security_event(
                    ldap_id=ldap_id,
                    event_type="INVALID_LLM_JSON",
                    severity="warning",
                    resume_id=str(resume.id),
                    section_type=stdef.key,
                    endpoint=request.path,
                    ip_address=ip_address,
                    metadata={"error": err_msg, "raw_snippet": str(raw_output)[:300]},
                )
                entry.generation_status = "failed"
                entry.save(update_fields=["generation_status"])
                return Response(
                    {
                        "error": "invalid_llm_json",
                        "message": f"LLM output failed schema validation: {err_msg}",
                    },
                    status=status.HTTP_502_BAD_GATEWAY,
                )

            # 6. Handle valid empty JSON as off-topic input
            if is_empty:
                record_user_violation(
                    ldap_id=ldap_id,
                    event_type="OFF_TOPIC_INPUT",
                    severity="info",
                    resume_id=str(resume.id),
                    section_type=stdef.key,
                    endpoint=request.path,
                    ip_address=ip_address,
                    metadata={"input_snippet": entry.raw_input[:200]},
                )
                entry.generation_status = "failed"
                entry.save(update_fields=["generation_status"])
                return Response(
                    {
                        "error": "invalid_resume_content",
                        "message": "The input does not appear to contain content relevant to this resume section.",
                    },
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY,
                )

            # Measure bullet widths and repair out-of-band ones (1 LLM retry).
            raw_output = fit_bullets_in_content(raw_output, stdef.key, llm)

            entry.content = raw_output
            entry.generation_status = "done"
            entry.save(update_fields=["content", "generation_status", "updated_at"])

            resume.latex_cache_valid = False
            resume.save(update_fields=["latex_cache_valid"])

            return Response(SectionEntrySerializer(entry).data)

        except LLMClientError as exc:
            log_security_event(
                ldap_id=ldap_id,
                event_type="LLM_PROVIDER_ERROR",
                severity="warning",
                resume_id=str(resume.id),
                section_type=stdef.key,
                endpoint=request.path,
                ip_address=ip_address,
                metadata={"error": str(exc)},
            )
            entry.generation_status = "failed"
            entry.save(update_fields=["generation_status"])
            return Response(
                {
                    "error": "llm_provider_error",
                    "message": "The AI service could not complete this request. Please try again later.",
                    "details": str(exc),
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception as exc:
            entry.generation_status = "failed"
            entry.save(update_fields=["generation_status"])
            return Response(
                {"error": "internal_error", "message": str(exc)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
