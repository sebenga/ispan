"""Base Django settings for iSpan."""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BASE_DIR.parent

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(BASE_DIR / ".env")


def env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def env_bool(key: str, default: bool = False) -> bool:
    raw = os.environ.get(key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def env_int(key: str, default: int) -> int:
    try:
        return int(os.environ[key])
    except (KeyError, ValueError):
        return default


def env_list(key: str, default: str = "") -> list[str]:
    raw = os.environ.get(key, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


SECRET_KEY = env("DJANGO_SECRET_KEY", "insecure-dev-key-change-me")
DEBUG = env_bool("DJANGO_DEBUG", False)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "apps.core",
    "apps.common",
    "apps.accounts",
    "apps.legal",
    "apps.workers",
    "apps.customers",
    "apps.services",
    "apps.catalog",
    "apps.jobs",
    "apps.scheduling",
    "apps.payments",
    "apps.ratings",
    "apps.disputes",
    "apps.notifications",
    "apps.safety",
    "apps.billing",
    "apps.partners",
    "apps.audit",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.spa.SpaFallbackMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASE_URL = env("DATABASE_URL")
if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=bool(env("RENDER")),
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-za"
TIME_ZONE = "Africa/Johannesburg"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "mediafiles"
PRIVATE_MEDIA_ROOT = env("PRIVATE_MEDIA_ROOT", str(BASE_DIR / "private_media"))
SPA_DIR = env("SPA_DIR", str(PROJECT_ROOT / "frontend" / "www"))

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:8100,http://localhost:4200,http://localhost:8000",
)
CSRF_TRUSTED_ORIGINS = env_list(
    "CSRF_TRUSTED_ORIGINS",
    "http://localhost:8100,http://localhost:4200,http://localhost:8000",
)

PUBLIC_APP_ORIGIN = env("PUBLIC_APP_ORIGIN", "http://localhost:8100")
PUBLIC_API_ORIGIN = env("PUBLIC_API_ORIGIN", "http://localhost:8000")

REDIS_URL = env("REDIS_URL", "redis://localhost:6379/0")
REALTIME_EVENT_CHANNEL = env("REALTIME_EVENT_CHANNEL", "ispan:events")
REALTIME_POLLING = env_bool("REALTIME_POLLING", False)
JOBS_INLINE = env_bool("JOBS_INLINE", True)

JWT_SIGNING_KEY = env("JWT_SIGNING_KEY", SECRET_KEY)
INTERNAL_API_TOKEN = env("INTERNAL_API_TOKEN", "dev-internal-token")

COMMISSION_BPS = env_int("COMMISSION_BPS", 1250)  # suggested starting point: 12.5%
PAYMENT_PROVIDER = env("PAYMENT_PROVIDER", "mock")
MOCK_WEBHOOK_SECRET = env("MOCK_WEBHOOK_SECRET", "dev-mock-webhook-secret")
PAYSTACK_SECRET_KEY = env("PAYSTACK_SECRET_KEY")
PAYSTACK_PUBLIC_KEY = env("PAYSTACK_PUBLIC_KEY")

LEGAL_VERSION = env("LEGAL_VERSION", "2026-11-19")
DEFAULT_CURRENCY = env("DEFAULT_CURRENCY", "ZAR")
DEFAULT_TIMEZONE = env("DEFAULT_TIMEZONE", "Africa/Johannesburg")
FEATURE_PARTNER_OFFERS = env_bool("FEATURE_PARTNER_OFFERS", False)
ESCROW_AUTO_RELEASE_HOURS = env_int("ESCROW_AUTO_RELEASE_HOURS", 24)
OFFER_SECONDS = env_int("OFFER_SECONDS", 20)
MATCH_INITIAL_RADIUS_KM = env_int("MATCH_INITIAL_RADIUS_KM", 5)
CANCELLATION_LATE_FEE_BPS = env_int("CANCELLATION_LATE_FEE_BPS", 5000)
CANCELLATION_WINDOW_MINUTES = env_int("CANCELLATION_WINDOW_MINUTES", 120)
CASH_DEBT_BLOCK_CENTS = env_int("CASH_DEBT_BLOCK_CENTS", 15000)
MIN_PAYOUT_CENTS = env_int("MIN_PAYOUT_CENTS", 10000)
KYC_PROVIDER = env("KYC_PROVIDER", "mock")
SMS_PROVIDER = env("SMS_PROVIDER", "mock")
MEDIA_ENCRYPTION_KEY = env("MEDIA_ENCRYPTION_KEY", "")

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env_int("JWT_ACCESS_MINUTES", 60)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env_int("JWT_REFRESH_DAYS", 14)),
    "SIGNING_KEY": JWT_SIGNING_KEY,
    "ALGORITHM": "HS256",
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "iSpan API",
    "DESCRIPTION": "Marketplace API for informal trades in South Africa",
    "VERSION": "0.1.0",
}

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
