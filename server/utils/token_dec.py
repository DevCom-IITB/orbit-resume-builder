import os
import requests
from functools import wraps
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.conf import settings


REACH_VERIFY = os.getenv(
    "REACH_VERIFY_URL", "http://127.0.0.1:8000/api/sso/accounts/verify/"
)
SERVICE_KEY = os.getenv("RB_SERVICE_KEY", "dev-resume-key-1")


def token_required(view_func):
    @wraps(view_func)
    def _wrapped(*args, **kwargs):
        if not args:
            return JsonResponse({"error": "Invalid request"}, status=500)

        # Support function-based views and class-based view methods.
        if hasattr(args[0], "META"):
            request = args[0]
            bound_args = args
        else:
            if len(args) < 2:
                return JsonResponse({"error": "Invalid request"}, status=500)
            request = args[1]
            bound_args = args

        if hasattr(request, "user") and request.user and request.user.is_authenticated:
            return view_func(*bound_args, **kwargs)


        auth_header = request.headers.get("Authorization") or request.META.get(
            "HTTP_AUTHORIZATION"
        )
        if not auth_header or not auth_header.startswith("Bearer "):
            return JsonResponse(
                {"error": "Authorization header missing or invalid"}, status=401
            )

        token = auth_header.split(" ")[1]

        try:
            resp = requests.get(
                REACH_VERIFY,
                headers={
                    "Authorization": f"Bearer {token}",
                    "X-Service-Key": SERVICE_KEY,
                },
                timeout=5,
            )
        except Exception:
            return JsonResponse({"error": "Failed to reach REACH"}, status=502)

        if resp.status_code != 200:
            try:
                return JsonResponse(resp.json(), status=resp.status_code)
            except Exception:
                return JsonResponse({"error": "Invalid token"}, status=401)

        data = resp.json()
        username = data.get("user")
        if not username:
            return JsonResponse({"error": "Invalid response from REACH"}, status=500)

        User = get_user_model()
        user, _ = User.objects.get_or_create(username=username)
        request.user = user
        return view_func(*bound_args, **kwargs)

    return _wrapped
