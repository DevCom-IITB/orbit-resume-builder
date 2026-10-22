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

# GitHub project import. Optional: when unset, the GitHub endpoints return 503
# instead of the whole server failing to start.
GITHUB_CLIENT_ID = env("GITHUB_CLIENT_ID", default="")
GITHUB_CLIENT_SECRET = env("GITHUB_CLIENT_SECRET", default="")
GITHUB_REDIRECT_URI = env("GITHUB_REDIRECT_URI", default="")
GITHUB_ENABLED = bool(GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET and GITHUB_REDIRECT_URI)
# `read:user` only reads public repos. Set to "repo read:user" to import private
# repos — note that `repo` also grants write access to them.
GITHUB_OAUTH_SCOPE = env("GITHUB_OAUTH_SCOPE", default="read:user")

# Origins of the REACH app that embeds Orbit. Tokens are only ever posted to,
# and accepted from, these origins.
REACH_ORIGINS = env.list(
    "REACH_ORIGINS", default=["http://localhost:3000"] if DEBUG else []
)

# Shared secret between Orbit and REACH's verify endpoint. The well-known dev
# value is only allowed with DEBUG; in production an unset key fails closed.
RB_SERVICE_KEY = env(
    "RB_SERVICE_KEY", default="dev-resume-key-1" if DEBUG else ""
)

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
