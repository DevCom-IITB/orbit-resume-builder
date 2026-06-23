from django.urls import path

from .views import (
    EntryDetail,
    EntryListCreate,
    GenerateEntryView,
    RenderResumeView,
    ResumeDetail,
    ResumeListCreate,
    ResumeDuplicate,
    SectionDetail,
    SectionListCreate,
    TemplateListView,
    VisualThemeListView,
)

urlpatterns = [
    path("templates/", TemplateListView.as_view()),
    path("themes/", VisualThemeListView.as_view()),
    path("", ResumeListCreate.as_view()),
    path("<uuid:resume_id>/", ResumeDetail.as_view()),
    path("<uuid:resume_id>/duplicate/", ResumeDuplicate.as_view()),
    path("<uuid:resume_id>/render/", RenderResumeView.as_view()),
    path("<uuid:resume_id>/sections/", SectionListCreate.as_view()),
    path("<uuid:resume_id>/sections/<uuid:section_id>/", SectionDetail.as_view()),
    path("<uuid:resume_id>/sections/<uuid:section_id>/entries/", EntryListCreate.as_view()),
    path(
        "<uuid:resume_id>/sections/<uuid:section_id>/entries/<uuid:entry_id>/",
        EntryDetail.as_view(),
    ),
    path(
        "<uuid:resume_id>/sections/<uuid:section_id>/entries/<uuid:entry_id>/generate/",
        GenerateEntryView.as_view(),
    ),
]
