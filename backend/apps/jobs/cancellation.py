"""Cancellation fee calculation using the job's snapshotted policy."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.utils import timezone

from .models import Job


def build_cancellation_policy_text(*, fee_bps: int, window_minutes: int) -> str:
    pct = fee_bps / 100
    hours = window_minutes / 60
    return (
        f"Free cancellation until {hours:g} hours before the scheduled start "
        f"(or before a worker accepts an instant job). After that, a late-cancellation "
        f"fee of {pct:g}% of the agreed amount applies. Exact amounts are calculated "
        f"at cancel time from the rules snapshotted when you booked."
    )


def is_late_cancellation(job: Job, *, now=None) -> bool:
    now = now or timezone.now()
    window = timedelta(minutes=job.cancel_window_minutes or 120)

    if job.status in {
        Job.Status.REQUESTED,
        Job.Status.OFFERED,
        Job.Status.QUOTED,
        Job.Status.EXPIRED,
    }:
        return False

    if job.scheduled_at:
        return now >= (job.scheduled_at - window)

    # Instant jobs: free until accepted; late once accepted/en route/etc.
    return job.status in {
        Job.Status.ACCEPTED,
        Job.Status.EN_ROUTE,
        Job.Status.ARRIVED,
        Job.Status.IN_PROGRESS,
        Job.Status.COMPLETED,
        Job.Status.CONFIRMED,
    }


def calculate_cancellation_fee(
    job: Job,
    *,
    actor,
    now=None,
) -> dict[str, Any]:
    """
    Return a fee snapshot for both roles and both payment methods.

    Customer late-cancel: customer owes fee; worker may receive fee minus commission.
    Worker late-cancel / no-show: worker is penalised (debt for cash; fee recorded);
    customer pays R0 and is fully refunded digitally when Phase 4 settles.
    """
    now = now or timezone.now()
    late = is_late_cancellation(job, now=now)
    base = job.agreed_price_cents or job.budget_cents or 0
    fee_bps = job.cancel_fee_bps or 0
    fee_cents = 0 if not late else round(base * fee_bps / 10000)
    commission_bps = job.commission_bps or 0
    commission_on_fee = round(fee_cents * commission_bps / 10000) if fee_cents else 0
    worker_share = max(fee_cents - commission_on_fee, 0)

    is_customer = actor.id == job.customer_id
    is_worker = job.worker_id and actor.id == job.worker_id

    if not late:
        return {
            "is_late": False,
            "fee_cents": 0,
            "base_cents": base,
            "fee_bps": fee_bps,
            "cancelled_by": "customer" if is_customer else "worker" if is_worker else "other",
            "customer_owes_cents": 0,
            "worker_receives_cents": 0,
            "worker_debt_cents": 0,
            "platform_commission_cents": 0,
            "escrow_refund_cents": base if job.payment_method == Job.PaymentMethod.ESCROW else 0,
            "payment_method": job.payment_method,
            "policy_window_minutes": job.cancel_window_minutes,
        }

    if is_customer:
        return {
            "is_late": True,
            "fee_cents": fee_cents,
            "base_cents": base,
            "fee_bps": fee_bps,
            "cancelled_by": "customer",
            "customer_owes_cents": fee_cents,
            "worker_receives_cents": worker_share,
            "worker_debt_cents": 0,
            "platform_commission_cents": commission_on_fee,
            "escrow_refund_cents": max(base - fee_cents, 0)
            if job.payment_method == Job.PaymentMethod.ESCROW
            else 0,
            "payment_method": job.payment_method,
            "policy_window_minutes": job.cancel_window_minutes,
        }

    # Worker late cancel
    return {
        "is_late": True,
        "fee_cents": fee_cents,
        "base_cents": base,
        "fee_bps": fee_bps,
        "cancelled_by": "worker",
        "customer_owes_cents": 0,
        "worker_receives_cents": 0,
        "worker_debt_cents": fee_cents if job.payment_method == Job.PaymentMethod.CASH else fee_cents,
        "platform_commission_cents": 0,
        "escrow_refund_cents": base if job.payment_method == Job.PaymentMethod.ESCROW else 0,
        "payment_method": job.payment_method,
        "policy_window_minutes": job.cancel_window_minutes,
    }
