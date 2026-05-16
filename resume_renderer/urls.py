from django.urls import path

from .views import LatexRenderView


urlpatterns = [
    path("render/", LatexRenderView.as_view(), name="latex-render"),
]
