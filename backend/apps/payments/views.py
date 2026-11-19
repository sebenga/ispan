from __future__ import annotations

import json

from django.conf import settings
from django.utils import timezone
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.jobs.models import Job

from .models import Payment, Payout, Receipt, WebhookEvent
from .services import (
    ensure_payment_for_job,
    process_webhook,
    request_payout,
    run_auto_releases,
    start_escrow_checkout,
)
from .wallet import get_or_create_wallet


class EscrowPayView(APIView):
    def post(self, request, job_id):
        try:
            job = Job.objects.select_related("payment").get(id=job_id)
        except Job.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)
        test_card = request.data.get("test_card", "succeed")
        try:
            result = start_escrow_checkout(job=job, customer=request.user, test_card=test_card)
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=403)
        except ValueError as exc:
            return Response({"detail": str(exc), "code": "payment_failed"}, status=402)
        payment = result["payment"]
        return Response(
            {
                "payment": {
                    "id": str(payment.id),
                    "status": payment.status,
                    "amount_cents": payment.amount_cents,
                    "commission_cents": payment.commission_cents,
                    "worker_payout_cents": payment.worker_payout_cents,
                    "provider": payment.provider,
                    "provider_ref": payment.provider_ref,
                    "failure_reason": payment.failure_reason,
                    "test_mode": True,
                },
                "checkout": result.get("checkout"),
                "awaiting_webhook": result.get("awaiting_webhook", False),
                "already_paid": result.get("already_paid", False),
                "test_cards": ["succeed", "fail", "insufficient_funds", "webhook_delay"],
            }
        )


class PaymentWebhookView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, provider: str):
        raw = request.body or b"{}"
        try:
            payload = json.loads(raw.decode() or "{}")
        except json.JSONDecodeError:
            payload = dict(request.data)
        event_id = (
            request.headers.get("X-Idempotency-Key")
            or payload.get("event_id")
            or payload.get("id")
            or f"{payload.get('reference')}:{payload.get('status')}"
        )
        try:
            result = process_webhook(
                provider=provider,
                event_id=str(event_id),
                payload=payload,
                headers={k: v for k, v in request.headers.items()},
                body=raw,
            )
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=401)
        return Response(result)


class WalletMeView(APIView):
    def get(self, request):
        wallet = get_or_create_wallet(request.user)
        return Response(
            {
                "available_cents": wallet.available_cents,
                "pending_cents": wallet.pending_cents,
                "debt_cents": wallet.debt_cents,
                "currency": wallet.currency,
                "debt_block_cents": settings.CASH_DEBT_BLOCK_CENTS,
                "blocked_from_accepts": wallet.debt_cents >= settings.CASH_DEBT_BLOCK_CENTS,
                "min_payout_cents": settings.MIN_PAYOUT_CENTS,
                "test_mode": settings.PAYMENT_PROVIDER == "mock",
            }
        )


class WalletLedgerView(APIView):
    def get(self, request):
        wallet = get_or_create_wallet(request.user)
        rows = [
            {
                "id": str(e.id),
                "entry_type": e.entry_type,
                "amount_cents": e.amount_cents,
                "balance_available_after": e.balance_available_after,
                "balance_pending_after": e.balance_pending_after,
                "balance_debt_after": e.balance_debt_after,
                "job_id": str(e.job_id) if e.job_id else None,
                "created_at": e.created_at,
            }
            for e in wallet.ledger.all()[:100]
        ]
        return Response({"results": rows})


class PayoutCreateView(APIView):
    def post(self, request):
        amount = request.data.get("amount_cents")
        try:
            payout = request_payout(
                worker=request.user,
                amount_cents=int(amount) if amount is not None else None,
            )
        except PermissionError as exc:
            return Response({"detail": str(exc), "code": "fica_blocked"}, status=403)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(
            {
                "id": str(payout.id),
                "amount_cents": payout.amount_cents,
                "status": payout.status,
                "provider_ref": payout.provider_ref,
                "paid_at": payout.paid_at,
            },
            status=201,
        )


class JobReceiptView(APIView):
    def get(self, request, job_id):
        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)
        if request.user.id not in {job.customer_id, job.worker_id} and not request.user.is_staff:
            return Response({"detail": "Forbidden."}, status=403)
        receipt = Receipt.objects.filter(job=job, recipient=request.user).order_by("-created_at").first()
        if not receipt:
            # Try any receipt for staff/customer fallback
            receipt = Receipt.objects.filter(job=job).order_by("-created_at").first()
        if not receipt:
            return Response({"detail": "No receipt yet.", "code": "no_receipt"}, status=404)
        return Response(
            {
                "id": str(receipt.id),
                "kind": receipt.kind,
                "html_body": receipt.html_body,
                "totals": receipt.totals,
                "created_at": receipt.created_at,
            }
        )


class IsStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and (u.is_staff or u.is_superuser or getattr(u, "is_support", False)))


class AdminMockPaymentsView(APIView):
    permission_classes = [IsStaff]

    def get(self, request):
        payments = Payment.objects.select_related("job").order_by("-created_at")[:50]
        webhooks = WebhookEvent.objects.order_by("-created_at")[:50]
        return Response(
            {
                "test_mode": True,
                "provider": settings.PAYMENT_PROVIDER,
                "payments": [
                    {
                        "id": str(p.id),
                        "job_id": str(p.job_id),
                        "status": p.status,
                        "amount_cents": p.amount_cents,
                        "provider_ref": p.provider_ref,
                        "test_card": p.test_card,
                        "auto_release_at": p.auto_release_at,
                    }
                    for p in payments
                ],
                "webhooks": [
                    {
                        "id": str(w.id),
                        "provider": w.provider,
                        "event_id": w.event_id,
                        "processed": w.processed,
                        "result": w.result,
                        "created_at": w.created_at,
                    }
                    for w in webhooks
                ],
            }
        )

    def post(self, request):
        """Fire a mock webhook or run auto-release sweep."""
        action = request.data.get("action")
        if action == "auto_release":
            count = run_auto_releases()
            return Response({"released": count, "at": timezone.now()})
        if action == "fire_webhook":
            payment_id = request.data.get("payment_id")
            try:
                payment = Payment.objects.get(id=payment_id)
            except Payment.DoesNotExist:
                return Response({"detail": "Payment not found."}, status=404)
            payload = {
                "event_id": request.data.get("event_id") or f"admin-{payment.id}-{timezone.now().timestamp()}",
                "reference": payment.provider_ref,
                "status": request.data.get("status", "success"),
            }
            result = process_webhook(
                provider=payment.provider or "mock",
                event_id=payload["event_id"],
                payload=payload,
                headers={"X-Mock-Signature": ""},
                body=json.dumps(payload).encode(),
            )
            return Response(result)
        return Response({"detail": "Unknown action."}, status=400)
