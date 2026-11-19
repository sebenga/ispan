from django.urls import path

from .views import (
    AdminMockPaymentsView,
    EscrowPayView,
    JobReceiptView,
    PaymentWebhookView,
    PayoutCreateView,
    WalletLedgerView,
    WalletMeView,
)

urlpatterns = [
    path("jobs/<uuid:job_id>/pay/escrow/", EscrowPayView.as_view(), name="job-pay-escrow"),
    path("jobs/<uuid:job_id>/receipt/", JobReceiptView.as_view(), name="job-receipt"),
    path("payments/webhooks/<str:provider>/", PaymentWebhookView.as_view(), name="payment-webhook"),
    path("wallets/me/", WalletMeView.as_view(), name="wallet-me"),
    path("wallets/me/ledger/", WalletLedgerView.as_view(), name="wallet-ledger"),
    path("wallets/me/payouts/", PayoutCreateView.as_view(), name="wallet-payouts"),
    path("admin/payments/mock/", AdminMockPaymentsView.as_view(), name="admin-mock-payments"),
]
