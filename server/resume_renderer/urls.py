from django.urls import path
from .views import *
from .views import LatexRenderView
from .views import refine_resume_section

urlpatterns = [
    path("render/", LatexRenderView.as_view(), name="latex-render"),
    path("<str:section_type>/", refine_resume_section, name="refine_resume_section"),
    path(
        "github/repositories/",
        GitHubRepositoriesAPIView.as_view(),
        name="github-repositories",
    ),
    path(
        "github/import-projects/",
        GitHubImportProjectsAPIView.as_view(),
        name="github-import-projects",
    ),
    path(
        "github/connect/",
        GitHubConnectAPIView.as_view(),
        name="github-connect",
    ),
    path(
        "github/status/",
        GitHubStatusAPIView.as_view(),
        name="github-status",
    ),
    path(
        "github/callback/",
        GitHubCallbackAPIView.as_view(),
        name="github-callback",
    ),
]
