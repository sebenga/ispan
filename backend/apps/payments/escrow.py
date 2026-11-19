"""
Escrow lifecycle for digital pre-pay jobs.

PENDING → AUTHORIZED → HELD → RELEASED | REFUNDED
Cash: CASH_PENDING → CASH_CONFIRMED
"""

from __future__ import annotations

from django.conf import settings
from django.utils import timezone

from .models import Payment, PaymentLedger
from .providers import charge_card, refund_charge


def split_commission(amount_cents: int, commission_bps: int | None = None) -> tuple[int, int]:
    bps = commission_bps if commission_bps is not None else settings.COMMISSION_BPS
    commission = round(amount_cents * bps / 10000)
    return commission, amount_cents - commission


def create_payment_for_job(*, job, method: str, amount_cents: int, commission_bps: int) -> Payment:
    commission, payout = split_commission(amount_cents, commission_bps)
    payment = Payment.objects.create(
        job=job,
        method=method,
        status=Payment.Status.CASH_PENDING if method == Payment.Method.CASH else Payment.Status.PENDING,
        amount_cents=amount_cents,
        commission_cents=commission,
        worker_payout_cents=payout,
        provider=settings.PAYMENT_PROVIDER,
    )
    PaymentLedger.objects.create(
        payment=payment,
        event="created",
        amount_cents=amount_cents,
        meta={"method": method},
    )
    return payment


def authorize_escrow(payment: Payment, email: str) -> Payment:
    if payment.method != Payment.Method.ESCROW:
        raise ValueError("Not an escrow payment")
    if payment.status != Payment.Status.PENDING:
        raise ValueError(f"Cannot authorize from {payment.status}")

    charge = charge_card(
        amount_cents=payment.amount_cents,
        email=email,
        reference=f"ispan_{payment.id}",
    )
    payment.status = Payment.Status.AUTHORIZED
    payment.provider_ref = charge["reference"]
    payment.save(update_fields=["status", "provider_ref", "updated_at"])
    PaymentLedger.objects.create(
        payment=payment,
        event="authorize",
        amount_cents=payment.amount_cents,
        meta=charge,
    )
    return payment


def hold_escrow(payment: Payment) -> Payment:
    if payment.status not in {Payment.Status.AUTHORIZED, Payment.Status.PENDING}:
        raise ValueError(f"Cannot hold from {payment.status}")
    payment.status = Payment.Status.HELD
    payment.held_at = timezone.now()
    payment.save(update_fields=["status", "held_at", "updated_at"])
    PaymentLedger.objects.create(payment=payment, event="hold", amount_cents=payment.amount_cents)
    return payment


def release_escrow(payment: Payment) -> Payment:
    if payment.status not in {Payment.Status.HELD, Payment.Status.AUTHORIZED}:
        raise ValueError(f"Cannot release from {payment.status}")
    payment.status = Payment.Status.RELEASED
    payment.released_at = timezone.now()
    payment.save(update_fields=["status", "released_at", "updated_at"])
    PaymentLedger.objects.create(
        payment=payment,
        event="release",
        amount_cents=payment.worker_payout_cents,
        meta={"commission_cents": payment.commission_cents},
    )
    return payment


def refund_escrow(payment: Payment, amount_cents: int | None = None) -> Payment:
    if payment.status not in {Payment.Status.HELD, Payment.Status.AUTHORIZED}:
        raise ValueError(f"Cannot refund from {payment.status}")
    refund_amount = amount_cents if amount_cents is not None else payment.amount_cents
    if payment.provider_ref:
        refund_charge(reference=payment.provider_ref, amount_cents=refund_amount)
    payment.status = Payment.Status.REFUNDED
    payment.refunded_at = timezone.now()
    payment.save(update_fields=["status", "refunded_at", "updated_at"])
    PaymentLedger.objects.create(payment=payment, event="refund", amount_cents=refund_amount)
    return payment


def confirm_cash(payment: Payment) -> Payment:
    if payment.method != Payment.Method.CASH:
        raise ValueError("Not a cash payment")
    payment.status = Payment.Status.CASH_CONFIRMED
    payment.released_at = timezone.now()
    payment.save(update_fields=["status", "released_at", "updated_at"])
    PaymentLedger.objects.create(
        payment=payment,
        event="cash_confirm",
        amount_cents=payment.amount_cents,
        meta={"commission_cents": payment.commission_cents},
    )
    return payment
