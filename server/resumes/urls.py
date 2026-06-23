from django.urls import path
from .views import ResumeListCreate, ResumeDetail, ResumeDuplicate

urlpatterns = [
    path("", ResumeListCreate.as_view(), name="resumes_list_create"),
    path(
        "<uuid:resume_id>/duplicate/",
        ResumeDuplicate.as_view(),
        name="resume_duplicate",
    ),
    path("<uuid:resume_id>/", ResumeDetail.as_view(), name="resume_detail"),
]
