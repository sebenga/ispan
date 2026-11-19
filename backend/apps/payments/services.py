from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import WorkerProfile
from apps.core.bus import publish_event

from .models import Payment, PaymentLedger, Payout, Receipt, WebhookEvent
from .providers import get_provider
from .wallet import (
    add_debt,
    credit_job_pending,
    get_or_create_wallet,
    move_pending_to_available,
)


def split_commission(amount_cents: int, commission_bps: int | None = None) -> tuple[int, int]:
    bps = commission_bps if commission_bps is not None else settings.COMMISSION_BPS
    commission = round(amount_cents * bps / 10000)
    return commission, amount_cents - commission


def ensure_payment_for_job(job) -> Payment:
    existing = getattr(job, "payment", None)
    if existing:
        return existing
    amount = job.agreed_price_cents or job.budget_cents or 0
    commission_bps = job.commission_bps or settings.COMMISSION_BPS
    commission, payout = split_commission(amount, commission_bps)
    method = job.payment_method
    status = (
        Payment.Status.CASH_PENDING
        if method == Payment.Method.CASH
        else Payment.Status.PENDING
    )
    payment = Payment.objects.create(
        job=job,
        method=method,
        status=status,
        amount_cents=amount,
        commission_bps=commission_bps,
        commission_cents=commission,
        worker_payout_cents=payout,
        provider=settings.PAYMENT_PROVIDER,
    )
    PaymentLedger.objects.create(
        payment=payment,
        event="created",
        amount_cents=amount,
        meta={"method": method},
        idempotency_key=f"created:{payment.id}",
    )
    return payment


def start_escrow_checkout(*, job, customer, test_card: str = "succeed") -> dict:
    """Not fully atomic — failed card attempts must persist as FAILED."""
    if job.customer_id != customer.id:
        raise PermissionError("Only the customer can pay for this job.")
    if job.payment_method != Payment.Method.ESCROW:
        raise ValueError("Job is not an escrow job.")
    payment = ensure_payment_for_job(job)
    if payment.status in {Payment.Status.HELD, Payment.Status.RELEASED}:
        return {"payment": payment, "already_paid": True}

    amount = job.agreed_price_cents or job.budget_cents or payment.amount_cents
    commission_bps = job.commission_bps or payment.commission_bps
    commission, payout = split_commission(amount, commission_bps)
    payment.amount_cents = amount
    payment.commission_bps = commission_bps
    payment.commission_cents = commission
    payment.worker_payout_cents = payout
    payment.test_card = test_card
    payment.failure_reason = ""
    payment.save()

    provider = get_provider(payment.provider or "mock")
    reference = f"ispan_{payment.id}"
    result = provider.create_checkout(
        amount_cents=payment.amount_cents,
        currency=payment.currency,
        reference=reference,
        email=customer.email,
        test_card=test_card,
        metadata={"job_id": str(job.id), "payment_id": str(payment.id)},
    )
    payment.provider = provider.name
    payment.provider_ref = result.get("reference", reference)

    if result.get("status") == "failed":
        payment.status = Payment.Status.FAILED
        payment.failure_reason = result.get("error", "Payment failed")
        payment.save()
        PaymentLedger.objects.update_or_create(
            payment=payment,
            idempotency_key=f"failed:{payment.id}:{test_card}",
            defaults={"event": "failed", "amount_cents": payment.amount_cents, "meta": result},
        )
        raise ValueError(payment.failure_reason)

    if result.get("status") == "pending":
        payment.status = Payment.Status.AUTHORIZED
        payment.save()
        PaymentLedger.objects.update_or_create(
            payment=payment,
            idempotency_key=f"authorize_pending:{payment.id}",
            defaults={
                "event": "authorize_pending_webhook",
                "amount_cents": payment.amount_cents,
                "meta": result,
            },
        )
        return {"payment": payment, "checkout": result, "awaiting_webhook": True}

    payment.status = Payment.Status.AUTHORIZED
    payment.save()
    PaymentLedger.objects.update_or_create(
        payment=payment,
        idempotency_key=f"authorize:{payment.id}",
        defaults={"event": "authorize", "amount_cents": payment.amount_cents, "meta": result},
    )
    hold_escrow(payment)
    return {"payment": payment, "checkout": result, "awaiting_webhook": False}


def hold_escrow(payment: Payment) -> Payment:
    if payment.status in {Payment.Status.HELD, Payment.Status.RELEASED}:
        return payment
    if payment.status not in {Payment.Status.AUTHORIZED, Payment.Status.PENDING}:
        raise ValueError(f"Cannot hold from {payment.status}")
    payment.status = Payment.Status.HELD
    payment.held_at = timezone.now()
    payment.save(update_fields=["status", "held_at", "updated_at"])
    PaymentLedger.objects.get_or_create(
        payment=payment,
        idempotency_key=f"hold:{payment.id}",
        defaults={"event": "hold", "amount_cents": payment.amount_cents, "meta": {}},
    )
    return payment


@transaction.atomic
def process_webhook(*, provider: str, event_id: str, payload: dict, headers: dict, body: bytes) -> dict:
    prov = get_provider(provider)
    if not prov.verify_webhook(headers=headers, body=body, payload=payload):
        raise PermissionError("Invalid webhook signature.")

    existing = WebhookEvent.objects.filter(provider=provider, event_id=event_id).first()
    if existing and existing.processed:
        return {"duplicate": True, "result": existing.result}

    event, _ = WebhookEvent.objects.get_or_create(
        provider=provider,
        event_id=event_id,
        defaults={"payload": payload},
    )
    if event.processed:
        return {"duplicate": True, "result": event.result}

    reference = payload.get("reference") or payload.get("provider_ref")
    payment = Payment.objects.select_for_update().filter(provider_ref=reference).first()
    if not payment:
        event.processed = True
        event.result = "payment_not_found"
        event.processed_at = timezone.now()
        event.save()
        return {"duplicate": False, "result": "payment_not_found"}

    status = (payload.get("status") or "").lower()
    if status in {"success", "authorized", "held", "paid"}:
        if payment.status == Payment.Status.RELEASED:
            result = "already_released"
        else:
            hold_escrow(payment)
            result = "held"
    elif status in {"failed", "fail"}:
        payment.status = Payment.Status.FAILED
        payment.failure_reason = payload.get("error", "Webhook reported failure")
        payment.save()
        result = "failed"
    else:
        result = "ignored"

    event.processed = True
    event.result = result
    event.processed_at = timezone.now()
    event.payload = payload
    event.save()
    return {"duplicate": False, "result": result, "payment_id": str(payment.id)}


@transaction.atomic
def settle_job_on_confirm(*, job) -> dict:
    """Customer confirmed completion — release escrow or record cash debt."""
    payment = ensure_payment_for_job(job)
    if payment.frozen:
        raise ValueError("Payment frozen by dispute.")
    if not job.worker_id:
        raise ValueError("No worker assigned.")

    wallet = get_or_create_wallet(job.worker)
    result: dict = {"method": payment.method}

    if payment.method == Payment.Method.ESCROW:
        if payment.status not in {Payment.Status.HELD, Payment.Status.AUTHORIZED, Payment.Status.RELEASED}:
            raise ValueError("Escrow is not held — customer must pay first.")
        if payment.status != Payment.Status.RELEASED:
            payment.status = Payment.Status.RELEASED
            payment.released_at = timezone.now()
            payment.save(update_fields=["status", "released_at", "updated_at"])
            PaymentLedger.objects.get_or_create(
                payment=payment,
                idempotency_key=f"release:{payment.id}",
                defaults={
                    "event": "release",
                    "amount_cents": payment.worker_payout_cents,
                    "meta": {"commission_cents": payment.commission_cents},
                },
            )
        credit_job_pending(wallet, job=job, amount_cents=payment.worker_payout_cents)
        move_pending_to_available(wallet, job=job, amount_cents=payment.worker_payout_cents)
        result["worker_credited_cents"] = payment.worker_payout_cents
        result["commission_cents"] = payment.commission_cents
    else:
        payment.status = Payment.Status.CASH_CONFIRMED
        payment.released_at = timezone.now()
        payment.save(update_fields=["status", "released_at", "updated_at"])
        PaymentLedger.objects.get_or_create(
            payment=payment,
            idempotency_key=f"cash_confirm:{payment.id}",
            defaults={
                "event": "cash_confirm",
                "amount_cents": payment.amount_cents,
                "meta": {"commission_cents": payment.commission_cents},
            },
        )
        if payment.commission_cents:
            add_debt(
                wallet,
                job=job,
                amount_cents=payment.commission_cents,
                entry_type="commission_debt",
                key=f"commission_debt:{job.id}",
            )
        result["worker_debt_cents"] = payment.commission_cents

    _issue_receipts(job, payment)
    wallet.refresh_from_db()
    publish_event(
        event="wallet:updated",
        rooms=[f"user:{job.worker_id}"],
        payload={
            "available_cents": wallet.available_cents,
            "pending_cents": wallet.pending_cents,
            "debt_cents": wallet.debt_cents,
        },
    )
    return result


def schedule_auto_release(job) -> None:
    payment = getattr(job, "payment", None)
    if not payment or payment.method != Payment.Method.ESCROW:
        return
    hours = settings.ESCROW_AUTO_RELEASE_HOURS
    payment.auto_release_at = timezone.now() + timedelta(hours=hours)
    payment.save(update_fields=["auto_release_at", "updated_at"])


@transaction.atomic
def run_auto_releases(*, now=None) -> int:
    now = now or timezone.now()
    qs = Payment.objects.select_for_update().filter(
        method=Payment.Method.ESCROW,
        status=Payment.Status.HELD,
        frozen=False,
        auto_release_at__lte=now,
        job__status="COMPLETED",
    )
    count = 0
    for payment in qs:
        job = payment.job
        if hasattr(job, "dispute") and job.dispute_id:
            continue
        # Treat auto-release like customer confirm for money, without changing job status here.
        # Job remains COMPLETED; money moves. Confirm status can still be set separately.
        if not job.worker_id:
            continue
        wallet = get_or_create_wallet(job.worker)
        payment.status = Payment.Status.RELEASED
        payment.released_at = now
        payment.save(update_fields=["status", "released_at", "updated_at"])
        PaymentLedger.objects.get_or_create(
            payment=payment,
            idempotency_key=f"release:{payment.id}",
            defaults={
                "event": "auto_release",
                "amount_cents": payment.worker_payout_cents,
                "meta": {"commission_cents": payment.commission_cents},
            },
        )
        credit_job_pending(wallet, job=job, amount_cents=payment.worker_payout_cents)
        move_pending_to_available(wallet, job=job, amount_cents=payment.worker_payout_cents)
        _issue_receipts(job, payment)
        count += 1
    return count


@transaction.atomic
def settle_cancellation_fees(*, job, snapshot: dict) -> None:
    payment = getattr(job, "payment", None)
    fee = snapshot.get("fee_cents") or 0
    if payment and payment.method == Payment.Method.ESCROW and payment.status in {
        Payment.Status.HELD,
        Payment.Status.AUTHORIZED,
    }:
        refund = snapshot.get("escrow_refund_cents")
        refund_escrow(payment, refund if refund is not None else payment.amount_cents)

    if not fee:
        return
    if snapshot.get("cancelled_by") == "customer" and job.worker_id:
        wallet = get_or_create_wallet(job.worker)
        worker_share = snapshot.get("worker_receives_cents") or 0
        if worker_share and payment and payment.method == Payment.Method.ESCROW:
            # Already deducted from refund; credit worker share to available
            append_key = f"cancel_fee_credit:{job.id}"
            from .wallet import append_ledger

            append_ledger(
                wallet=wallet,
                entry_type="cancel_fee_credit",
                amount_cents=worker_share,
                available_delta=worker_share,
                job=job,
                idempotency_key=append_key,
            )
    if snapshot.get("cancelled_by") == "worker" and job.worker_id:
        wallet = get_or_create_wallet(job.worker)
        add_debt(
            wallet,
            job=job,
            amount_cents=fee,
            entry_type="cancel_fee_debt",
            key=f"cancel_fee_debt:{job.id}",
        )


def refund_escrow(payment: Payment, amount_cents: int | None = None) -> Payment:
    if payment.status not in {
        Payment.Status.HELD,
        Payment.Status.AUTHORIZED,
        Payment.Status.PARTIALLY_REFUNDED,
    }:
        raise ValueError(f"Cannot refund from {payment.status}")
    refund_amount = amount_cents if amount_cents is not None else payment.amount_cents
    provider = get_provider(payment.provider or "mock")
    if payment.provider_ref:
        provider.refund(provider_ref=payment.provider_ref, amount_cents=refund_amount)
    if refund_amount >= payment.amount_cents:
        payment.status = Payment.Status.REFUNDED
    else:
        payment.status = Payment.Status.PARTIALLY_REFUNDED
    payment.refunded_at = timezone.now()
    payment.save(update_fields=["status", "refunded_at", "updated_at"])
    PaymentLedger.objects.get_or_create(
        payment=payment,
        idempotency_key=f"refund:{payment.id}:{refund_amount}",
        defaults={"event": "refund", "amount_cents": refund_amount, "meta": {}},
    )
    return payment


@transaction.atomic
def request_payout(*, worker, amount_cents: int | None = None) -> Payout:
    profile = getattr(worker, "worker_profile", None)
    if not profile or profile.verification_status != WorkerProfile.VerificationStatus.VERIFIED:
        raise PermissionError("Payouts require a verified worker (FICA/KYC gate).")
    if not profile.bank_verified:
        raise PermissionError("Bank account must be verified before payout.")

    wallet = get_or_create_wallet(worker)
    wallet = type(wallet).objects.select_for_update().get(pk=wallet.pk)
    amount = amount_cents if amount_cents is not None else wallet.available_cents
    if amount < settings.MIN_PAYOUT_CENTS:
        raise ValueError(f"Minimum payout is {settings.MIN_PAYOUT_CENTS} cents.")
    if amount > wallet.available_cents:
        raise ValueError("Insufficient available balance.")

    bank = {}
    if hasattr(profile, "bank_account") and profile.bank_account:
        bank = {
            "bank_name": profile.bank_account.bank_name,
            "account_masked": profile.bank_account.account_number_masked,
            "holder_name": profile.bank_account.holder_name,
        }
    else:
        bank = {"account_masked": profile.bank_account_masked}

    payout = Payout.objects.create(
        wallet=wallet,
        amount_cents=amount,
        status=Payout.Status.PENDING,
        provider=settings.PAYMENT_PROVIDER,
        bank_snapshot=bank,
    )
    provider = get_provider()
    result = provider.transfer_to_wallet(
        amount_cents=amount,
        destination={"user_id": str(worker.id), **bank},
    )
    # Clear debt from payout if any
    debt_clear = min(wallet.debt_cents, amount)
    from .wallet import append_ledger

    append_ledger(
        wallet=wallet,
        entry_type="payout",
        amount_cents=-amount,
        available_delta=-amount,
        job=None,
        idempotency_key=f"payout:{payout.id}",
        metadata=result,
    )
    if debt_clear:
        append_ledger(
            wallet=wallet,
            entry_type="payout_debt_clear",
            amount_cents=-debt_clear,
            debt_delta=-debt_clear,
            job=None,
            idempotency_key=f"payout_debt_clear:{payout.id}",
        )

    payout.status = Payout.Status.PAID
    payout.provider_ref = result.get("reference", "")
    payout.paid_at = timezone.now()
    payout.save()
    return payout


def _issue_receipts(job, payment: Payment) -> None:
    totals = {
        "amount_cents": payment.amount_cents,
        "commission_cents": payment.commission_cents,
        "worker_payout_cents": payment.worker_payout_cents,
        "currency": payment.currency,
        "method": payment.method,
        "status": payment.status,
    }
    entity = "[full legal name]"
    for kind, user in (("customer", job.customer), ("worker", job.worker)):
        if not user:
            continue
        html = (
            f"<h1>iSpan receipt</h1>"
            f"<p>Legal entity: {entity}</p>"
            f"<p>Job: {job.title}</p>"
            f"<p>Amount: R{payment.amount_cents/100:.2f}</p>"
            f"<p>Commission: R{payment.commission_cents/100:.2f}</p>"
            f"<p>Worker payout: R{payment.worker_payout_cents/100:.2f}</p>"
            f"<p>Method: {payment.method} · Status: {payment.status}</p>"
        )
        Receipt.objects.update_or_create(
            job=job,
            recipient=user,
            kind=kind,
            defaults={"payment": payment, "html_body": html, "totals": totals},
        )


# Back-compat aliases for escrow.py
create_payment_for_job = ensure_payment_for_job
