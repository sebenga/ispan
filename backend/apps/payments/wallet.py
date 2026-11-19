from __future__ import annotations

from django.conf import settings
from django.db import transaction

from .models import Wallet, WalletLedger


def get_or_create_wallet(user) -> Wallet:
    wallet, _ = Wallet.objects.get_or_create(worker=user)
    return wallet


def worker_debt_blocks_accepts(user) -> bool:
    wallet = getattr(user, "wallet", None)
    if wallet is None:
        try:
            wallet = Wallet.objects.get(worker=user)
        except Wallet.DoesNotExist:
            return False
    return wallet.debt_cents >= settings.CASH_DEBT_BLOCK_CENTS


@transaction.atomic
def append_ledger(
    *,
    wallet: Wallet,
    entry_type: str,
    amount_cents: int,
    idempotency_key: str,
    job=None,
    metadata: dict | None = None,
    available_delta: int = 0,
    pending_delta: int = 0,
    debt_delta: int = 0,
) -> WalletLedger:
    if WalletLedger.objects.filter(idempotency_key=idempotency_key).exists():
        return WalletLedger.objects.get(idempotency_key=idempotency_key)

    wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
    wallet.available_cents += available_delta
    wallet.pending_cents += pending_delta
    wallet.debt_cents += debt_delta
    if wallet.available_cents < 0 or wallet.pending_cents < 0 or wallet.debt_cents < 0:
        raise ValueError("Wallet balance cannot go negative.")
    wallet.save(update_fields=["available_cents", "pending_cents", "debt_cents", "updated_at"])

    return WalletLedger.objects.create(
        wallet=wallet,
        job=job,
        entry_type=entry_type,
        amount_cents=amount_cents,
        balance_available_after=wallet.available_cents,
        balance_pending_after=wallet.pending_cents,
        balance_debt_after=wallet.debt_cents,
        idempotency_key=idempotency_key,
        metadata=metadata or {},
    )


def credit_job_pending(wallet: Wallet, *, job, amount_cents: int) -> WalletLedger:
    return append_ledger(
        wallet=wallet,
        entry_type=WalletLedger.EntryType.JOB_PENDING,
        amount_cents=amount_cents,
        pending_delta=amount_cents,
        job=job,
        idempotency_key=f"job_pending:{job.id}",
        metadata={"job_id": str(job.id)},
    )


def move_pending_to_available(wallet: Wallet, *, job, amount_cents: int) -> WalletLedger:
    return append_ledger(
        wallet=wallet,
        entry_type=WalletLedger.EntryType.JOB_AVAILABLE,
        amount_cents=amount_cents,
        pending_delta=-amount_cents,
        available_delta=amount_cents,
        job=job,
        idempotency_key=f"job_available:{job.id}",
        metadata={"job_id": str(job.id)},
    )


def add_debt(wallet: Wallet, *, job, amount_cents: int, entry_type: str, key: str) -> WalletLedger:
    return append_ledger(
        wallet=wallet,
        entry_type=entry_type,
        amount_cents=amount_cents,
        debt_delta=amount_cents,
        job=job,
        idempotency_key=key,
        metadata={"job_id": str(job.id) if job else None},
    )
