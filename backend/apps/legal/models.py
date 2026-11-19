from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.core.models import UUIDModel


class LegalConsent(UUIDModel):
    """POPIA / ECTA consent record (logged-in or anonymous)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="legal_consents",
    )
    anon_id = models.CharField(max_length=64, blank=True, db_index=True)
    version = models.CharField(max_length=32)
    flags = models.JSONField(default=dict)
    accepted_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        ordering = ["-accepted_at"]

    def __str__(self) -> str:
        who = self.user_id or self.anon_id or "unknown"
        return f"Consent {self.version} by {who}"
