from __future__ import annotations

from typing import Any

from .base import PaymentProvider


class _NotConfigured(PaymentProvider):
    name = "placeholder"

    def create_checkout(self, **kwargs) -> dict[str, Any]:
        raise RuntimeError(f"{self.name} is not configured.")

    def capture(self, **kwargs) -> dict[str, Any]:
        raise RuntimeError(f"{self.name} is not configured.")

    def refund(self, **kwargs) -> dict[str, Any]:
        raise RuntimeError(f"{self.name} is not configured.")

    def transfer_to_wallet(self, **kwargs) -> dict[str, Any]:
        raise RuntimeError(f"{self.name} is not configured.")

    def verify_webhook(self, **kwargs) -> bool:
        return False


class PayFastProvider(_NotConfigured):
    name = "payfast"


class YocoProvider(_NotConfigured):
    name = "yoco"


class PaystackProvider(_NotConfigured):
    name = "paystack"


class OzowProvider(_NotConfigured):
    name = "ozow"
