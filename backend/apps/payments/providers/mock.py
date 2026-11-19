from __future__ import annotations

import hashlib
import hmac
from typing import Any

from django.conf import settings

from .base import PaymentProvider

TEST_CARDS = {
    "succeed": {"ok": True, "result": "success"},
    "success": {"ok": True, "result": "success"},
    "fail": {"ok": False, "result": "failed", "error": "Card declined (mock)."},
    "insufficient_funds": {
        "ok": False,
        "result": "failed",
        "error": "Insufficient funds (mock).",
    },
    "webhook_delay": {"ok": True, "result": "pending", "delay": True},
}


class MockProvider(PaymentProvider):
    name = "mock"

    def create_checkout(
        self,
        *,
        amount_cents: int,
        currency: str,
        reference: str,
        email: str,
        test_card: str = "succeed",
        metadata: dict | None = None,
    ) -> dict[str, Any]:
        card = (test_card or "succeed").strip().lower()
        spec = TEST_CARDS.get(card) or TEST_CARDS["fail"]
        if not spec["ok"]:
            return {
                "provider": self.name,
                "reference": reference,
                "status": "failed",
                "error": spec.get("error", "Payment failed"),
                "test_card": card,
            }
        status = "pending" if spec.get("delay") else "authorized"
        return {
            "provider": self.name,
            "reference": reference,
            "status": status,
            "checkout_url": f"{settings.PUBLIC_APP_ORIGIN}/customer/pay/mock?ref={reference}",
            "test_card": card,
            "amount_cents": amount_cents,
            "currency": currency,
            "email": email,
            "metadata": metadata or {},
        }

    def capture(self, *, provider_ref: str, amount_cents: int) -> dict[str, Any]:
        return {"provider": self.name, "reference": provider_ref, "status": "captured", "amount_cents": amount_cents}

    def refund(self, *, provider_ref: str, amount_cents: int) -> dict[str, Any]:
        return {"provider": self.name, "reference": provider_ref, "status": "refunded", "amount_cents": amount_cents}

    def transfer_to_wallet(self, *, amount_cents: int, destination: dict) -> dict[str, Any]:
        return {
            "provider": self.name,
            "status": "paid",
            "amount_cents": amount_cents,
            "destination": destination,
            "reference": f"mock_payout_{amount_cents}",
        }

    def verify_webhook(self, *, headers: dict, body: bytes, payload: dict) -> bool:
        secret = getattr(settings, "MOCK_WEBHOOK_SECRET", settings.INTERNAL_API_TOKEN)
        # Header lookup is case-insensitive via normalized map
        normalized = {str(k).lower(): v for k, v in (headers or {}).items()}
        sig = normalized.get("x-mock-signature") or ""
        if not sig:
            # Dev / test convenience: unsigned mock webhooks allowed outside production.
            return not getattr(settings, "IS_PRODUCTION", False)
        expected = hmac.new(secret.encode(), body or b"", hashlib.sha256).hexdigest()
        return hmac.compare_digest(sig, expected)
