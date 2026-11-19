from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class PaymentProvider(ABC):
    name: str = "base"

    @abstractmethod
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
        ...

    @abstractmethod
    def capture(self, *, provider_ref: str, amount_cents: int) -> dict[str, Any]:
        ...

    @abstractmethod
    def refund(self, *, provider_ref: str, amount_cents: int) -> dict[str, Any]:
        ...

    @abstractmethod
    def transfer_to_wallet(self, *, amount_cents: int, destination: dict) -> dict[str, Any]:
        ...

    @abstractmethod
    def verify_webhook(self, *, headers: dict, body: bytes, payload: dict) -> bool:
        ...
