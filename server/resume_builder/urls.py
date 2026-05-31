"""URL configuration for the standalone resume_builder project."""

from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/sso/", include("ssoAuth.urls")),
    path("api/resume-renderer/", include("resume_renderer.urls")),
    path("api/bridge/", include("bridge.urls")),
    path("api/resumes/", include("resumes.urls")),
]
