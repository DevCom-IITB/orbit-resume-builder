import os
import json
import requests
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

# Simple proxy endpoint to validate token with REACH verify endpoint
# POST /api/bridge/verify_reach/ with JSON { token: '...' }

REACH_VERIFY = os.getenv('REACH_VERIFY_URL', 'http://127.0.0.1:8000/api/sso/accounts/verify/')
SERVICE_KEY = os.getenv('RB_SERVICE_KEY', 'dev-resume-key-1')


@csrf_exempt
@require_POST
def verify_reach(request):
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'error': 'invalid json'}, status=400)

    token = data.get('token')
    if not token:
        return JsonResponse({'error': 'missing token'}, status=400)

    try:
        resp = requests.get(REACH_VERIFY, headers={'Authorization': f'Bearer {token}', 'X-Service-Key': SERVICE_KEY}, timeout=5)
    except Exception:
        return JsonResponse({'error': 'request failed'}, status=502)

    return JsonResponse(resp.json(), status=resp.status_code)
