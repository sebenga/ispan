from __future__ import annotations

import hashlib
import secrets

from django.conf import settings


def generate_pin(length: int = 4) -> str:
    upper = 10**length
    return f"{secrets.randbelow(upper):0{length}d}"


def hash_pin(pin: str) -> str:
    pepper = settings.SECRET_KEY
    return hashlib.sha256(f"{pepper}:pin:{pin}".encode()).hexdigest()


def verify_pin(pin: str, pin_hash: str) -> bool:
    if not pin or not pin_hash:
        return False
    return hash_pin(pin.strip()) == pin_hash
