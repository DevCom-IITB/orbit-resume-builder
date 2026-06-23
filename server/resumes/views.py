from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.paginator import Paginator
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from .serializers import ResumeSerializer
from .models import Resume, Section, Version
from utils.token_dec import token_required


@method_decorator(csrf_exempt, name="dispatch")
class ResumeListCreate(APIView):
    @token_required
    def get(self, request):
        qs = Resume.objects.filter(owner=request.user).order_by(
            "-is_pinned", "-updated_at"
        )
        page = request.GET.get("page", 1)
        per = int(request.GET.get("per", 10))
        paginator = Paginator(qs, per)
        result = paginator.get_page(page)
        serializer = ResumeSerializer(
            result.object_list, many=True, context={"request": request}
        )
        return Response(
            {
                "count": paginator.count,
                "num_pages": paginator.num_pages,
                "results": serializer.data,
            }
        )

    @token_required
    def post(self, request):
        data = request.data
        serializer = ResumeSerializer(data=data, context={"request": request})
        if serializer.is_valid():
            resume = serializer.save()
            return Response(
                ResumeSerializer(resume, context={"request": request}).data,
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name="dispatch")
class ResumeDetail(APIView):
    @token_required
    def get(self, request, resume_id):
        try:
            resume = Resume.objects.get(id=resume_id, owner=request.user)
        except Resume.DoesNotExist:
            return Response({"error": "not found"}, status=status.HTTP_404_NOT_FOUND)
        data = ResumeSerializer(resume, context={"request": request}).data
        return Response(data)

    @token_required
    def patch(self, request, resume_id):
        try:
            resume = Resume.objects.get(id=resume_id, owner=request.user)
        except Resume.DoesNotExist:
            return Response({"error": "not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = ResumeSerializer(
            resume, data=request.data, partial=True, context={"request": request}
        )
        if serializer.is_valid():
            updated = serializer.save()
            # create version snapshot
            Version.objects.create(
                resume=updated,
                snapshot=ResumeSerializer(updated, context={"request": request}).data,
                created_by=request.user,
            )
            return Response(
                ResumeSerializer(updated, context={"request": request}).data
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @token_required
    def delete(self, request, resume_id):
        try:
            resume = Resume.objects.get(id=resume_id, owner=request.user)
        except Resume.DoesNotExist:
            return Response({"error": "not found"}, status=status.HTTP_404_NOT_FOUND)
        resume.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator(csrf_exempt, name="dispatch")
class ResumeDuplicate(APIView):
    @token_required
    def post(self, request, resume_id):
        try:
            source = Resume.objects.get(id=resume_id, owner=request.user)
        except Resume.DoesNotExist:
            return Response({"error": "not found"}, status=status.HTTP_404_NOT_FOUND)

        new_resume = Resume.objects.create(
            owner=request.user,
            title=f"{source.title} (Copy)",
            resume_type=source.resume_type,
            header_type=source.header_type,
            meta=source.meta,
            is_pinned=False,
        )
        for section in source.sections.all():
            Section.objects.create(
                resume=new_resume,
                section_type=section.section_type,
                order=section.order,
                content=section.content,
            )

        return Response(
            ResumeSerializer(new_resume, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )
