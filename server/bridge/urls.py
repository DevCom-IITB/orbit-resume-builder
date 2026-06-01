from django.urls import path
from .views import verify_reach

urlpatterns = [
    path("verify_reach/", verify_reach, name="verify_reach"),
]
