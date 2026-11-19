from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.core.models import BaseModel, UUIDModel
from apps.jobs.models import Job


class EmergencyContact(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="emergency_contacts"
    )
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=20)
    relationship = models.CharField(max_length=80, blank=True)
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_primary", "name"]


class SosEvent(BaseModel):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        ACKNOWLEDGED = "ACKNOWLEDGED", "Acknowledged"
        RESOLVED = "RESOLVED", "Resolved"
        FALSE_ALARM = "FALSE_ALARM", "False alarm"

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="sos_events")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sos_events")
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)
    accuracy_m = models.FloatField(null=True, blank=True)
    note = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    notified_parties = models.JSONField(default=list, blank=True)
    support_notified = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="resolved_sos_events",
    )

    class Meta:
        ordering = ["-created_at"]


class SafetyFlag(BaseModel):
    class Kind(models.TextChoices):
        ABUSE = "abuse", "Abuse"
        FRAUD = "fraud", "Fraud"
        PROFANITY = "profanity", "Profanity"
        OTHER = "other", "Other"

    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="safety_flags"
    )
    job = models.ForeignKey(Job, null=True, blank=True, on_delete=models.SET_NULL, related_name="flags")
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.OTHER)
    details = models.TextField()
    status = models.CharField(max_length=20, default="OPEN")
