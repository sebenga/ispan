"""South African ID number format checks (not a Home Affairs verification)."""

from __future__ import annotations


def is_valid_sa_id(value: str) -> bool:
    """Validate 13-digit SA ID with Luhn checksum. Format check only."""
    digits = "".join(ch for ch in value if ch.isdigit())
    if len(digits) != 13:
        return False
    # Basic date YYMMDD sanity
    yy, mm, dd = int(digits[0:2]), int(digits[2:4]), int(digits[4:6])
    if mm < 1 or mm > 12 or dd < 1 or dd > 31:
        return False
    # Luhn
    total = 0
    for i, ch in enumerate(digits):
        n = int(ch)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def mask_id_number(value: str) -> str:
    digits = "".join(ch for ch in value if ch.isdigit())
    if len(digits) < 4:
        return "****"
    return f"{'*' * (len(digits) - 4)}{digits[-4:]}"
