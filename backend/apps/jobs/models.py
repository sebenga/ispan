from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.catalog.models import ServiceCategory
from apps.core.models import BaseModel, UUIDModel


class Job(BaseModel):
    class Status(models.TextChoices):
        REQUESTED = "REQUESTED", "Requested"
        OFFERED = "OFFERED", "Offered"
        QUOTED = "QUOTED", "Quoted"
        ACCEPTED = "ACCEPTED", "Accepted"
        EN_ROUTE = "EN_ROUTE", "En route"
        ARRIVED = "ARRIVED", "Arrived"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        COMPLETED = "COMPLETED", "Completed"
        CONFIRMED = "CONFIRMED", "Confirmed"
        CANCELLED = "CANCELLED", "Cancelled"
        EXPIRED = "EXPIRED", "Expired"
        DISPUTED = "DISPUTED", "Disputed"

    class Mode(models.TextChoices):
        INSTANT = "instant", "Instant"
        SCHEDULED = "scheduled", "Scheduled"

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
    status = models.CharField(
        max_length=32, choices=Status.choices, default=Status.REQUESTED, db_index=True
    )
    mode = models.CharField(max_length=16, choices=Mode.choices, default=Mode.INSTANT)
    payment_method = models.CharField(max_length=16, choices=PaymentMethod.choices)
    currency = models.CharField(max_length=3, default="ZAR")
    budget_cents = models.PositiveIntegerField(null=True, blank=True)
    agreed_price_cents = models.PositiveIntegerField(null=True, blank=True)
    commission_bps = models.PositiveIntegerField(default=1250)
    # Cancellation policy snapshot at booking (catalogue changes must not rewrite history).
    cancel_fee_bps = models.PositiveIntegerField(default=5000)
    cancel_window_minutes = models.PositiveIntegerField(default=120)
    cancellation_policy_text = models.TextField(blank=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    is_immediate = models.BooleanField(default=True)  # legacy alias of mode=instant
    address_line = models.CharField(max_length=255)
    suburb = models.CharField(max_length=120)
    city = models.CharField(max_length=80, default="Cape Town")
    region = models.CharField(max_length=80, default="Western Cape")
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)
    women_preferred = models.BooleanField(default=False)
    accept_cancellation_policy = models.BooleanField(default=False)
    # Matching state
    match_radius_km = models.FloatField(default=5)
    match_round = models.PositiveSmallIntegerField(default=0)
    last_match_at = models.DateTimeField(null=True, blank=True)
    # PINs hashed; plaintext returned once via API to the customer.
    start_pin_hash = models.CharField(max_length=128, blank=True)
    finish_pin_hash = models.CharField(max_length=128, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cancelled_jobs",
    )
    cancellation_fee_cents = models.PositiveIntegerField(null=True, blank=True)
    cancellation_snapshot = models.JSONField(default=dict, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.title} [{self.status}]"


class JobOffer(BaseModel):
    class Status(models.TextChoices):
        NOTIFIED = "notified", "Notified"
        SEEN = "seen", "Seen"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        EXPIRED = "expired", "Expired"
        LOST_RACE = "lost_race", "Lost race"

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="offers")
    worker = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="job_offers"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NOTIFIED)
    distance_km = models.FloatField(null=True, blank=True)
    notified_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    seen_at = models.DateTimeField(null=True, blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-notified_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["job", "worker"],
                condition=models.Q(status__in=["notified", "seen"]),
                name="uniq_active_offer_per_worker",
            ),
        ]


class Quote(BaseModel):
    class Status(models.TextChoices):
        PROPOSED = "proposed", "Proposed"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"
        WITHDRAWN = "withdrawn", "Withdrawn"

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="quotes")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    amount_cents = models.PositiveIntegerField()
    message = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PROPOSED)

    class Meta:
        ordering = ["-created_at"]


class JobEvent(UUIDModel):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="events")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    event_type = models.CharField(max_length=40)
    from_status = models.CharField(max_length=32, blank=True)
    to_status = models.CharField(max_length=32, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class JobTracking(UUIDModel):
    """Coarse location breadcrumb for an active job only (POPIA — short retention)."""

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="tracking")
    lat = models.FloatField()
    lng = models.FloatField()
    accuracy_m = models.FloatField(null=True, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="job_location_pings",
    )
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-recorded_at"]


class Message(UUIDModel):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


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
