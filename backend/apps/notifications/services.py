from __future__ import annotations

import logging

from django.conf import settings

from .models import MockNotification

logger = logging.getLogger(__name__)


def send_notification(
    *,
    channel: str,
    destination: str,
    template: str,
    body: str,
    subject: str = "",
    user=None,
    payload: dict | None = None,
) -> MockNotification | None:
    provider = getattr(settings, "SMS_PROVIDER", "mock") if channel == "sms" else "mock"
    # Never log OTP codes or full message bodies with secrets in production logs.
    logger.info("notification channel=%s template=%s dest=%s", channel, template, _mask(destination))

    if provider == "mock" or True:  # Phase 1: always mock
        return MockNotification.objects.create(
            user=user,
            channel=channel,
            destination=destination,
            template=template,
            subject=subject,
            body=body,
            payload=payload or {},
        )
    return None


def _mask(destination: str) -> str:
    if "@" in destination:
        name, _, domain = destination.partition("@")
        return f"{name[:2]}***@{domain}"
    digits = "".join(ch for ch in destination if ch.isdigit())
    return f"***{digits[-3:]}" if len(digits) >= 3 else "***"
