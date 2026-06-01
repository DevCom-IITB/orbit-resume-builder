import base64
import json
import os
from urllib.parse import urlencode

import requests
from django.contrib.auth import get_user_model, login
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken

from utils.token_dec import token_required

CLIENT_ID = os.getenv('SSO_CLIENT_ID', '')
CLIENT_SECRET = os.getenv('SSO_CLIENT_SECRET', '')
REDIRECT_URI = os.getenv(
    'SSO_REDIRECT_URI',
    'http://127.0.0.1:8000/api/sso/accounts/callback/',
)
AUTH_TOKEN = os.getenv('SSO_AUTHENTICATION_TOKEN', '')
AUTH_URL = 'https://gymkhana.iitb.ac.in/profiles/oauth/authorize/'
TOKEN_URL = 'https://gymkhana.iitb.ac.in/profiles/oauth/token/'
PROFILE_URL = 'https://gymkhana.iitb.ac.in/profiles/user/api/user/?fields=first_name,last_name,type,profile_picture,sex,username,email,program,contacts,insti_address,secondary_emails,mobile,roll_number'
REVOKE_URL = 'https://gymkhana.iitb.ac.in/profiles/oauth/revoke_token/'


def _basic_auth_token() -> str:
    if AUTH_TOKEN:
        return AUTH_TOKEN
    if CLIENT_ID and CLIENT_SECRET:
        raw = f'{CLIENT_ID}:{CLIENT_SECRET}'.encode('utf-8')
        return base64.b64encode(raw).decode('utf-8')
    return ''


@api_view(['GET'])
@permission_classes([AllowAny])
def gymkhana_login(request):
    params = urlencode(
        {
            'client_id': CLIENT_ID,
            'response_type': 'code',
            'scope': 'basic profile ldap program',
            'redirect_uri': REDIRECT_URI,
            'state': 'secure_random_state',
        }
    )
    return redirect(f'{AUTH_URL}?{params}')


@api_view(['GET'])
@permission_classes([AllowAny])
def gymkhana_callback(request):
    code = request.GET.get('code')
    if not code:
        return JsonResponse({'error': 'Authorization code missing'}, status=400)

    auth_token = _basic_auth_token()
    if not auth_token:
        return JsonResponse({'error': 'SSO client credentials are not configured'}, status=500)

    data = {'code': code, 'redirect_uri': REDIRECT_URI, 'grant_type': 'authorization_code'}
    headers = {
        'Authorization': f'Basic {auth_token}',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    }

    try:
        response = requests.post(TOKEN_URL, data=data, headers=headers, timeout=10)
        response.raise_for_status()
        token_data = response.json()
    except requests.RequestException:
        return JsonResponse({'error': 'Token request failed'}, status=400)
    except ValueError:
        return JsonResponse({'error': 'Invalid response from token endpoint'}, status=400)

    access_token = token_data.get('access_token')
    if not access_token:
        return JsonResponse({'error': 'Access token not provided', 'details': token_data}, status=400)

    profile_headers = {'Authorization': f'Bearer {access_token}'}
    try:
        profile_response = requests.get(PROFILE_URL, headers=profile_headers, timeout=10)
        profile_response.raise_for_status()
        profile_data = profile_response.json()
    except requests.RequestException:
        return JsonResponse({'error': 'Profile request failed'}, status=400)
    except ValueError:
        return JsonResponse({'error': 'Invalid response from profile endpoint'}, status=400)

    username = profile_data.get('username')
    if not username:
        return JsonResponse({'error': 'Username not provided in profile data'}, status=400)

    email = profile_data.get('email', '')
    first_name = profile_data.get('first_name', '')
    last_name = profile_data.get('last_name', '')
    full_name = f'{first_name} {last_name}'.strip() or username

    user_model = get_user_model()
    user, _ = user_model.objects.get_or_create(username=username, defaults={'email': email or None})
    user.email = email or user.email
    user.first_name = first_name or user.first_name
    user.last_name = last_name or user.last_name
    user.save(update_fields=['email', 'first_name', 'last_name'])

    login(request, user)
    refresh = RefreshToken.for_user(user)

    payload = {
        'detail': 'Successfully logged in',
        'role': 'unknown',
        'user': username,
        'full_name': full_name,
        'access_token': str(refresh.access_token),
        'refresh_token': str(refresh),
    }

    response_html = f"""<!doctype html>
<html>
  <body>
    <script>
      const payload = {json.dumps(payload)};
      try {{
        if (window.opener && !window.opener.closed) {{
          window.opener.postMessage({{ type: 'REACH_TOKEN', token: payload.access_token }}, '*');
        }}
        if (window.parent && window.parent !== window) {{
          window.parent.postMessage({{ type: 'REACH_TOKEN', token: payload.access_token }}, '*');
        }}
      }} finally {{
        document.body.innerText = 'Login successful. You may close this tab.';
        setTimeout(() => window.close(), 500);
      }}
    </script>
    <noscript>{json.dumps(payload)}</noscript>
  </body>
</html>"""
    return HttpResponse(response_html, content_type='text/html')


@api_view(['POST'])
def refresh_token(request):
    refresh_value = request.data.get('refresh_token')
    if not refresh_value:
        return JsonResponse({'error': 'No refresh token found'}, status=400)

    try:
        refresh = RefreshToken(refresh_value)
        return JsonResponse(
            {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }
        )
    except Exception:
        return JsonResponse({'error': 'Invalid refresh token'}, status=400)


@api_view(['POST'])
@token_required
def revoke_token(request):
    return JsonResponse({'message': 'Token revoked client-side'})


@api_view(['GET'])
@token_required
def user_profile(request):
    user = request.user
    return Response(
        {
            'role': 'unknown',
            'profile': {
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
            },
        }
    )


class VerifyView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        service_key = request.headers.get('X-Service-Key') or request.META.get('HTTP_X_SERVICE_KEY')
        if not service_key or service_key != os.getenv('RB_SERVICE_KEY', 'dev-resume-key-1'):
            return JsonResponse({'error': 'Invalid service key'}, status=403)

        return JsonResponse(
            {
                'user': request.user.username,
                'id': request.user.id,
                'role': 'unknown',
                'profile': {
                    'username': request.user.username,
                    'email': request.user.email,
                    'first_name': request.user.first_name,
                    'last_name': request.user.last_name,
                },
            }
        )
