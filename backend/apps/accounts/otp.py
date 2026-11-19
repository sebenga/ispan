from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from apps.notifications.services import send_notification

from .models import OtpChallenge, User

OTP_TTL_MINUTES = 10
DEV_FIXED_OTP = "123456"  # only used when DEBUG / mock — documented in README


def _hash_code(code: str) -> str:
    pepper = settings.SECRET_KEY
    return hashlib.sha256(f"{pepper}:{code}".encode()).hexdigest()


def request_otp(
    *,
    purpose: str,
    destination: str,
    user: User | None = None,
    channel: str = "sms",
) -> tuple[OtpChallenge, str]:
    """Create an OTP challenge. Returns (challenge, plain_code). Plain code is for mock inbox only."""
    OtpChallenge.objects.filter(
        destination=destination, purpose=purpose, consumed_at__isnull=True
    ).update(consumed_at=timezone.now())

    code = DEV_FIXED_OTP if settings.DEBUG or settings.SMS_PROVIDER == "mock" else f"{secrets.randbelow(10**6):06d}"
    challenge = OtpChallenge.objects.create(
        user=user,
        purpose=purpose,
        destination=destination,
        code_hash=_hash_code(code),
        expires_at=timezone.now() + timedelta(minutes=OTP_TTL_MINUTES),
    )
    body = f"Your iSpan code is {code}. It expires in {OTP_TTL_MINUTES} minutes."
    send_notification(
        channel=channel,
        destination=destination,
        template="otp",
        body=body,
        subject="iSpan verification code",
        user=user,
        payload={"purpose": purpose, "code_hint": "see mock inbox — never log code in prod"},
    )
    return challenge, code


def verify_otp(*, purpose: str, destination: str, code: str) -> OtpChallenge:
    challenge = (
        OtpChallenge.objects.filter(
            purpose=purpose, destination=destination, consumed_at__isnull=True
        )
        .order_by("-created_at")
        .first()
    )
    if not challenge:
        raise ValueError("No active code. Request a new one.")
    if challenge.expires_at < timezone.now():
        raise ValueError("Code expired. Request a new one.")
    if challenge.attempt_count >= challenge.max_attempts:
        raise ValueError("Too many attempts. Request a new code.")

    challenge.attempt_count += 1
    challenge.save(update_fields=["attempt_count"])

    if challenge.code_hash != _hash_code(code.strip()):
        raise ValueError("Invalid code.")

    challenge.consumed_at = timezone.now()
    challenge.save(update_fields=["consumed_at"])
    return challenge
