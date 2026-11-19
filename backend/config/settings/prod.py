import hashlib
import sys
from pathlib import Path

from .base import *  # noqa: F403
from .base import (
    ALLOWED_HOSTS,
    REST_FRAMEWORK,
    SECRET_KEY,
    SIMPLE_JWT,
    SPA_DIR,
    env,
    env_bool,
    env_int,
)

DEBUG = False

_BUILD_ONLY = {"collectstatic", "check", "compilemessages"}
if env("RENDER") and not env("DATABASE_URL") and not _BUILD_ONLY.intersection(sys.argv):
    raise RuntimeError("DATABASE_URL must be set on Render.")

if SECRET_KEY in {"", "insecure-dev-key-change-me"}:
    if env("RENDER"):
        material = env("RENDER_SERVICE_ID") or env("RENDER_EXTERNAL_HOSTNAME") or "ispan-render"
        SECRET_KEY = hashlib.sha256(f"ispan|{material}".encode()).hexdigest()
        JWT_SIGNING_KEY = env("JWT_SIGNING_KEY") or SECRET_KEY
        SIMPLE_JWT = {**SIMPLE_JWT, "SIGNING_KEY": JWT_SIGNING_KEY}
    else:
        raise RuntimeError("DJANGO_SECRET_KEY must be set in production.")

REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
}

SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", not bool(env("RENDER")))
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

CORS_ALLOW_ALL_ORIGINS = False
JOBS_INLINE = env_bool("JOBS_INLINE", bool(env("RENDER")))
REALTIME_POLLING = env_bool("REALTIME_POLLING", bool(env("RENDER")))

if Path(SPA_DIR).is_dir():
    WHITENOISE_ROOT = Path(SPA_DIR)

if env("RENDER"):
    render_host = env("RENDER_EXTERNAL_HOSTNAME")
    if render_host and render_host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS = [*ALLOWED_HOSTS, render_host]
