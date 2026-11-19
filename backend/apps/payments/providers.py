from __future__ import annotations

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def charge_card(*, amount_cents: int, email: str, reference: str) -> dict:
    provider = settings.PAYMENT_PROVIDER
    if provider == "paystack" and settings.PAYSTACK_SECRET_KEY:
        res = requests.post(
            "https://api.paystack.co/transaction/initialize",
            headers={
                "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "email": email,
                "amount": amount_cents,
                "reference": reference,
                "currency": "ZAR",
                "callback_url": f"{settings.PUBLIC_APP_ORIGIN}/api/v1/payments/webhook/",
            },
            timeout=30,
        )
        res.raise_for_status()
        data = res.json()["data"]
        return {"reference": data["reference"], "status": "success", "provider": "paystack"}

    return {"reference": reference, "status": "success", "provider": "mock"}


def refund_charge(*, reference: str, amount_cents: int) -> dict:
    if settings.PAYMENT_PROVIDER == "paystack" and settings.PAYSTACK_SECRET_KEY:
        res = requests.post(
            "https://api.paystack.co/refund",
            headers={
                "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
                "Content-Type": "application/json",
            },
            json={"transaction": reference, "amount": amount_cents},
            timeout=30,
        )
        res.raise_for_status()
    return {"status": "success"}
