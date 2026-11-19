from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.catalog.models import ServiceCategory
from apps.core.models import BaseModel, UUIDModel


class Job(BaseModel):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        MATCHED = "MATCHED", "Matched"
        ACCEPTED = "ACCEPTED", "Accepted"
        EN_ROUTE = "EN_ROUTE", "En route"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION", "Awaiting confirmation"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"
        DISPUTED = "DISPUTED", "Disputed"

    class PaymentMethod(models.TextChoices):
        ESCROW = "ESCROW", "Digital escrow"
        CASH = "CASH", "Cash"

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="customer_jobs"
    )
    worker = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="worker_jobs",
    )
    category = models.ForeignKey(ServiceCategory, on_delete=models.PROTECT, related_name="jobs")
    title = models.CharField(max_length=160)
    description = models.TextField()
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.OPEN, db_index=True)
    payment_method = models.CharField(max_length=16, choices=PaymentMethod.choices)
    budget_cents = models.PositiveIntegerField()
    agreed_price_cents = models.PositiveIntegerField(null=True, blank=True)
    commission_bps = models.PositiveIntegerField(default=1250)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    is_immediate = models.BooleanField(default=True)
    address_line = models.CharField(max_length=255)
    suburb = models.CharField(max_length=120)
    city = models.CharField(max_length=80, default="Cape Town")
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)
    cancel_fee_bps = models.PositiveIntegerField(default=5000)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cancelled_jobs",
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.title} [{self.status}]"


class JobTracking(UUIDModel):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="tracking")
    lat = models.FloatField()
    lng = models.FloatField()
    recorded_at = models.DateTimeField(auto_now_add=True)


class Message(UUIDModel):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class Rating(UUIDModel):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="ratings")
    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ratings_given"
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ratings_received"
    )
    score = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["job", "from_user"], name="uniq_job_rater"),
        ]


class Dispute(BaseModel):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        SUPPORT_REVIEW = "SUPPORT_REVIEW", "Support review"
        RESOLVED = "RESOLVED", "Resolved"
        APPEALED = "APPEALED", "Appealed"

    class Outcome(models.TextChoices):
        WARNING = "WARNING", "Warning"
        TEMP_SUSPENSION = "TEMP_SUSPENSION", "Temporary suspension"
        LONG_SUSPENSION = "LONG_SUSPENSION", "Long suspension"
        ACCOUNT_REVIEW = "ACCOUNT_REVIEW", "Account review"
        NO_ACTION = "NO_ACTION", "No action"

    job = models.OneToOneField(Job, on_delete=models.CASCADE, related_name="dispute")
    opened_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    reason = models.TextField()
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.OPEN)
    outcome = models.CharField(max_length=32, choices=Outcome.choices, blank=True)
    support_notes = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
