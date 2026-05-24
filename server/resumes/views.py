import json
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.paginator import Paginator

from .serializers import ResumeSerializer
from .models import Resume, Section, Version
from utils.token_dec import token_required


class ResumeListCreate(APIView):
    @token_required
    def get(self, request):
        qs = Resume.objects.filter(owner=request.user).order_by('-updated_at')
        page = request.GET.get('page', 1)
        per = int(request.GET.get('per', 10))
        paginator = Paginator(qs, per)
        result = paginator.get_page(page)
        serializer = ResumeSerializer(result.object_list, many=True, context={'request': request})
        return Response({
            'count': paginator.count,
            'num_pages': paginator.num_pages,
            'results': serializer.data,
        })

    @token_required
    def post(self, request):
        data = request.data
        serializer = ResumeSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            resume = serializer.save()
            return Response(ResumeSerializer(resume, context={'request': request}).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResumeDetail(APIView):
    @token_required
    def get(self, request, resume_id):
        try:
            resume = Resume.objects.get(id=resume_id, owner=request.user)
        except Resume.DoesNotExist:
            return Response({'error': 'not found'}, status=status.HTTP_404_NOT_FOUND)
        data = ResumeSerializer(resume, context={'request': request}).data
        return Response(data)

    @token_required
    def patch(self, request, resume_id):
        try:
            resume = Resume.objects.get(id=resume_id, owner=request.user)
        except Resume.DoesNotExist:
            return Response({'error': 'not found'}, status=status.HTTP_404_NOT_FOUND)

        serializer = ResumeSerializer(resume, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            updated = serializer.save()
            # create version snapshot
            Version.objects.create(resume=updated, snapshot=ResumeSerializer(updated, context={'request': request}).data, created_by=request.user)
            return Response(ResumeSerializer(updated, context={'request': request}).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @token_required
    def delete(self, request, resume_id):
        try:
            resume = Resume.objects.get(id=resume_id, owner=request.user)
        except Resume.DoesNotExist:
            return Response({'error': 'not found'}, status=status.HTTP_404_NOT_FOUND)
        resume.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
