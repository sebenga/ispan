from __future__ import annotations

from django.conf import settings

from .base import PaymentProvider
from .mock import MockProvider
from .placeholders import OzowProvider, PayFastProvider, PaystackProvider, YocoProvider

_PROVIDERS: dict[str, type[PaymentProvider]] = {
    "mock": MockProvider,
    "payfast": PayFastProvider,
    "yoco": YocoProvider,
    "paystack": PaystackProvider,
    "ozow": OzowProvider,
}


def get_provider(name: str | None = None) -> PaymentProvider:
    key = (name or getattr(settings, "PAYMENT_PROVIDER", "mock") or "mock").lower()
    cls = _PROVIDERS.get(key, MockProvider)
    return cls()


# Back-compat helpers used by older escrow module callers
def charge_card(*, amount_cents: int, email: str, reference: str) -> dict:
    return get_provider().create_checkout(
        amount_cents=amount_cents,
        currency="ZAR",
        reference=reference,
        email=email,
        test_card="succeed",
    )


def refund_charge(*, reference: str, amount_cents: int) -> dict:
    return get_provider().refund(provider_ref=reference, amount_cents=amount_cents)
