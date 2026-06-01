from django.urls import path

from .views import (
    gymkhana_callback,
    gymkhana_login,
    refresh_token,
    revoke_token,
    user_profile,
    VerifyView,
)

urlpatterns = [
    path("accounts/login/", gymkhana_login, name="gymkhana_login"),
    path("accounts/callback/", gymkhana_callback, name="gymkhana_callback"),
    path("accounts/verify/", VerifyView.as_view(), name="gymkhana_verify"),
    path("accounts/refresh/", refresh_token, name="refresh_token"),
    path("accounts/revoke/", revoke_token, name="revoke_token"),
    path("accounts/profile/", user_profile, name="user_profile"),
]
