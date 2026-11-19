"""Escrow helpers — thin wrappers around payments.services for back-compat."""

from __future__ import annotations

from .services import (
    create_payment_for_job,
    hold_escrow,
    refund_escrow,
    settle_job_on_confirm,
    split_commission,
    start_escrow_checkout,
)


def authorize_escrow(payment, email: str):
    # Legacy path: mark authorized then hold via checkout-equivalent.
    from django.utils import timezone

    from .models import Payment, PaymentLedger

    if payment.method != Payment.Method.ESCROW:
        raise ValueError("Not an escrow payment")
    payment.status = Payment.Status.AUTHORIZED
    payment.provider_ref = payment.provider_ref or f"ispan_{payment.id}"
    payment.save(update_fields=["status", "provider_ref", "updated_at"])
    PaymentLedger.objects.get_or_create(
        payment=payment,
        idempotency_key=f"authorize:{payment.id}",
        defaults={
            "event": "authorize",
            "amount_cents": payment.amount_cents,
            "meta": {"email": email, "at": timezone.now().isoformat()},
        },
    )
    return payment


def confirm_cash(payment):
    job = payment.job
    return settle_job_on_confirm(job=job)


def release_escrow(payment):
    job = payment.job
    return settle_job_on_confirm(job=job)


__all__ = [
    "split_commission",
    "create_payment_for_job",
    "authorize_escrow",
    "hold_escrow",
    "release_escrow",
    "refund_escrow",
    "confirm_cash",
    "start_escrow_checkout",
    "settle_job_on_confirm",
]
