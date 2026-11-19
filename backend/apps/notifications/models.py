from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.core.models import UUIDModel


class MockNotification(UUIDModel):
    """Dev inbox for mock SMS / email / WhatsApp (never a real gateway)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="mock_notifications",
    )
    channel = models.CharField(max_length=20)  # sms | email | push | whatsapp
    destination = models.CharField(max_length=255)
    template = models.CharField(max_length=80)
    subject = models.CharField(max_length=200, blank=True)
    body = models.TextField()
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
