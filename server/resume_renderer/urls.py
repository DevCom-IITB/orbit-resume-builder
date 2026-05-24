from django.urls import path

from .views import LatexRenderView
from .views import refine_resume_section

urlpatterns = [
    path("render/", LatexRenderView.as_view(), name="latex-render"),
    path("<str:section_type>/", refine_resume_section, name="refine_resume_section"),
]
