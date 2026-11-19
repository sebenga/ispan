from __future__ import annotations

from django.db import models

from apps.core.models import BaseModel, UUIDModel
from apps.jobs.models import Job


class Payment(BaseModel):
    class Method(models.TextChoices):
        ESCROW = "ESCROW", "Digital escrow"
        CASH = "CASH", "Cash"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        AUTHORIZED = "AUTHORIZED", "Authorized"
        HELD = "HELD", "Held"
        RELEASED = "RELEASED", "Released"
        REFUNDED = "REFUNDED", "Refunded"
        FAILED = "FAILED", "Failed"
        CASH_PENDING = "CASH_PENDING", "Cash pending"
        CASH_CONFIRMED = "CASH_CONFIRMED", "Cash confirmed"

    job = models.OneToOneField(Job, on_delete=models.CASCADE, related_name="payment")
    method = models.CharField(max_length=16, choices=Method.choices)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.PENDING)
    amount_cents = models.PositiveIntegerField()
    commission_cents = models.PositiveIntegerField()
    worker_payout_cents = models.PositiveIntegerField()
    provider = models.CharField(max_length=32, blank=True)  # paystack | mock
    provider_ref = models.CharField(max_length=120, blank=True)
    held_at = models.DateTimeField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"Payment<{self.job_id}:{self.status}>"


class PaymentLedger(UUIDModel):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="ledger")
    event = models.CharField(max_length=40)
    amount_cents = models.PositiveIntegerField()
    meta = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
