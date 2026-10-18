"""Django settings for the standalone resume-builder project."""

from pathlib import Path
from environ import Env

BASE_DIR = Path(__file__).resolve().parent.parent

env = Env()
env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")

# Development-only authentication shortcut.
# Leave empty unless you explicitly want to enable it.
DEV_AUTH_USERNAME = env("DEV_AUTH_USERNAME", default="")

GITHUB_CLIENT_ID = env("GITHUB_CLIENT_ID", default="")
GITHUB_CLIENT_SECRET = env("GITHUB_CLIENT_SECRET", default="")
GITHUB_REDIRECT_URI = env("GITHUB_REDIRECT_URI", default="")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "ssoAuth",
    "resume_renderer",
    "resumes",
    "rag",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "resume_builder.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "resume_builder.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = env.list("FRONTEND_URLS")
CORS_ALLOW_CREDENTIALS = True

# Allow Reach (localhost:3000) to embed Orbit in an iframe during local dev.
if DEBUG:
    X_FRAME_OPTIONS = "ALLOWALL"

# =========================
# Redis & LLM Rate Limiting / Security Configuration
# =========================
REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")
ORBIT_LLM_USER_30MIN_LIMIT = env.int("ORBIT_LLM_USER_30MIN_LIMIT", default=20)
ORBIT_LLM_USER_30MIN_WINDOW_SECONDS = env.int("ORBIT_LLM_USER_30MIN_WINDOW_SECONDS", default=1800)
ORBIT_LLM_USER_DAILY_LIMIT = env.int("ORBIT_LLM_USER_DAILY_LIMIT", default=100)
ORBIT_LLM_USER_DAILY_WINDOW_SECONDS = env.int("ORBIT_LLM_USER_DAILY_WINDOW_SECONDS", default=86400)
ORBIT_ABUSE_FIRST_BLOCK_SECONDS = env.int("ORBIT_ABUSE_FIRST_BLOCK_SECONDS", default=600)
ORBIT_ABUSE_SECOND_BLOCK_SECONDS = env.int("ORBIT_ABUSE_SECOND_BLOCK_SECONDS", default=3600)
ORBIT_ABUSE_THIRD_BLOCK_SECONDS = env.int("ORBIT_ABUSE_THIRD_BLOCK_SECONDS", default=86400)
