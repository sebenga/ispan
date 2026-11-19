from __future__ import annotations

from django.conf import settings
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
        RELEASED = "RELEASED", "Released to worker"
        REFUNDED = "REFUNDED", "Refunded"
        PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED", "Partially refunded"
        FAILED = "FAILED", "Failed"
        CASH_PENDING = "CASH_PENDING", "Cash pending"
        CASH_CONFIRMED = "CASH_CONFIRMED", "Cash confirmed"

    job = models.OneToOneField(Job, on_delete=models.CASCADE, related_name="payment")
    method = models.CharField(max_length=16, choices=Method.choices)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.PENDING)
    currency = models.CharField(max_length=3, default="ZAR")
    amount_cents = models.PositiveIntegerField()
    commission_bps = models.PositiveIntegerField(default=1250)
    commission_cents = models.PositiveIntegerField()
    worker_payout_cents = models.PositiveIntegerField()
    provider = models.CharField(max_length=32, blank=True)
    provider_ref = models.CharField(max_length=120, blank=True, db_index=True)
    test_card = models.CharField(max_length=40, blank=True)
    frozen = models.BooleanField(default=False)  # dispute freeze
    held_at = models.DateTimeField(null=True, blank=True)
    released_at = models.DateTimeField(null=True, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)
    auto_release_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.CharField(max_length=255, blank=True)

    def __str__(self) -> str:
        return f"Payment<{self.job_id}:{self.status}>"


class PaymentLedger(UUIDModel):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="ledger")
    event = models.CharField(max_length=40)
    amount_cents = models.PositiveIntegerField()
    meta = models.JSONField(default=dict, blank=True)
    idempotency_key = models.CharField(max_length=120, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["payment", "idempotency_key"],
                condition=~models.Q(idempotency_key=""),
                name="uniq_payment_ledger_idempotency",
            )
        ]


class WebhookEvent(UUIDModel):
    """Idempotent provider webhook inbox."""

    provider = models.CharField(max_length=32)
    event_id = models.CharField(max_length=120)
    payload = models.JSONField(default=dict)
    processed = models.BooleanField(default=False)
    result = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["provider", "event_id"], name="uniq_provider_event"),
        ]


class Wallet(BaseModel):
    worker = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wallet"
    )
    available_cents = models.IntegerField(default=0)
    pending_cents = models.IntegerField(default=0)
    debt_cents = models.IntegerField(default=0)
    currency = models.CharField(max_length=3, default="ZAR")

    def __str__(self) -> str:
        return f"Wallet<{self.worker_id}>"


class WalletLedger(UUIDModel):
    class EntryType(models.TextChoices):
        JOB_PENDING = "job_pending", "Job pending credit"
        JOB_AVAILABLE = "job_available", "Job available credit"
        COMMISSION_DEBT = "commission_debt", "Cash commission debt"
        CANCEL_FEE_DEBT = "cancel_fee_debt", "Cancellation fee debt"
        CANCEL_FEE_CREDIT = "cancel_fee_credit", "Cancellation fee credit"
        PAYOUT = "payout", "Payout"
        PAYOUT_DEBT_CLEAR = "payout_debt_clear", "Payout debt clear"
        ADJUSTMENT = "adjustment", "Adjustment"

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="ledger")
    job = models.ForeignKey(Job, null=True, blank=True, on_delete=models.SET_NULL)
    entry_type = models.CharField(max_length=32, choices=EntryType.choices)
    amount_cents = models.IntegerField()  # signed
    balance_available_after = models.IntegerField()
    balance_pending_after = models.IntegerField()
    balance_debt_after = models.IntegerField()
    idempotency_key = models.CharField(max_length=120, unique=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class Payout(BaseModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        FAILED = "FAILED", "Failed"
        BLOCKED = "BLOCKED", "Blocked"

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="payouts")
    amount_cents = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    provider = models.CharField(max_length=32, default="mock")
    provider_ref = models.CharField(max_length=120, blank=True)
    bank_snapshot = models.JSONField(default=dict, blank=True)
    failure_reason = models.CharField(max_length=255, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)


class Receipt(BaseModel):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="receipts")
    payment = models.ForeignKey(Payment, null=True, blank=True, on_delete=models.SET_NULL)
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    kind = models.CharField(max_length=20, default="customer")  # customer | worker
    html_body = models.TextField()
    totals = models.JSONField(default=dict, blank=True)
