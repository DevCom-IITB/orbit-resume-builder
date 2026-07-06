from django.urls import path
from .views import GitHubProjectsAPIView
from .views import LatexRenderView
from .views import refine_resume_section

urlpatterns = [
    path("render/", LatexRenderView.as_view(), name="latex-render"),
    path("<str:section_type>/", refine_resume_section, name="refine_resume_section"),
    path(
        'github/<str:username>/projects/', 
        GitHubProjectsAPIView.as_view(), 
        name='github-projects'
    ),
]
