from __future__ import annotations

import uuid
from pathlib import Path

from django.conf import settings

from apps.common.crypto import encrypt_bytes

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
}
MAX_BYTES = 5 * 1024 * 1024  # 5 MB


def private_media_root() -> Path:
    root = Path(getattr(settings, "PRIVATE_MEDIA_ROOT", settings.BASE_DIR / "private_media"))
    root.mkdir(parents=True, exist_ok=True)
    return root


def store_encrypted_upload(*, worker_id, doc_type: str, uploaded) -> tuple[str, str, int]:
    content_type = getattr(uploaded, "content_type", "") or "application/octet-stream"
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError("Unsupported file type. Use JPEG, PNG, WebP or PDF.")
    data = uploaded.read()
    if len(data) > MAX_BYTES:
        raise ValueError("File too large (max 5 MB).")
    if len(data) == 0:
        raise ValueError("Empty file.")

    encrypted = encrypt_bytes(data)
    rel = Path("workers") / str(worker_id) / doc_type / f"{uuid.uuid4()}.bin"
    dest = private_media_root() / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(encrypted)
    return str(rel), content_type, len(data)
