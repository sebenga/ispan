from __future__ import annotations

import mimetypes
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse, HttpResponseNotFound
from django.views.decorators.http import require_GET

# Never rewrite these to index.html — the browser needs the real bytes.
_ASSET_SUFFIXES = {
    ".js",
    ".css",
    ".map",
    ".json",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".txt",
    ".webmanifest",
}


def _index_path() -> Path | None:
    spa = Path(settings.SPA_DIR)
    for candidate in (spa / "index.html", spa / "browser" / "index.html"):
        if candidate.is_file():
            return candidate
    return None


def _spa_root() -> Path:
    return Path(settings.SPA_DIR)


def _is_asset(path: str) -> bool:
    return Path(path).suffix.lower() in _ASSET_SUFFIXES


def resolve_spa_file(url_path: str) -> Path | None:
    """Resolve a URL path to a file under SPA_DIR (no path traversal)."""
    root = _spa_root().resolve()
    relative = url_path.lstrip("/")
    if not relative:
        return _index_path()
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    if candidate.is_file():
        return candidate
    # Angular/Ionic sometimes nest under browser/
    nested = (root / "browser" / relative).resolve()
    try:
        nested.relative_to(root)
    except ValueError:
        return None
    if nested.is_file():
        return nested
    return None


@require_GET
def spa_index(request):
    path = _index_path()
    if not path:
        return HttpResponse(
            "<h1>iSpan</h1><p>SPA not built. Run <code>cd frontend && npm run build:prod</code>.</p>"
            "<p>For local UI use <a href='http://localhost:8100'>http://localhost:8100</a>.</p>",
            content_type="text/html",
        )
    return HttpResponse(path.read_text(encoding="utf-8"), content_type="text/html")


@require_GET
def spa_asset(request, asset_path: str):
    """Serve built SPA files (JS/CSS/assets) from SPA_DIR."""
    file_path = resolve_spa_file(asset_path)
    if not file_path:
        if _is_asset(asset_path):
            raise Http404("Asset not found")
        # Client-side route → index.html
        return spa_index(request)
    content_type, _ = mimetypes.guess_type(str(file_path))
    return FileResponse(file_path.open("rb"), content_type=content_type or "application/octet-stream")


def not_found(request, exception=None):
    if _is_asset(request.path):
        return HttpResponseNotFound("Not found")
    path = _index_path()
    if path and not request.path.startswith("/api/"):
        return HttpResponse(path.read_text(encoding="utf-8"), content_type="text/html")
    return HttpResponseNotFound("Not found")


class SpaFallbackMiddleware:
    """Serve index.html for deep links only — never for missing static assets."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Prefer real SPA files before Django 404s them into HTML.
        if request.method == "GET" and not request.path.startswith(
            ("/api/", "/admin/", "/internal/", "/healthz", "/static/", "/media/")
        ):
            asset = resolve_spa_file(request.path)
            if asset and asset.name != "index.html":
                content_type, _ = mimetypes.guess_type(str(asset))
                return FileResponse(
                    asset.open("rb"),
                    content_type=content_type or "application/octet-stream",
                )

        response = self.get_response(request)
        if (
            response.status_code == 404
            and request.method == "GET"
            and not request.path.startswith(("/api/", "/admin/", "/internal/", "/healthz"))
            and not _is_asset(request.path)
        ):
            path = _index_path()
            if path:
                return HttpResponse(path.read_text(encoding="utf-8"), content_type="text/html")
        return response
