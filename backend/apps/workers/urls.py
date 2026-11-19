from django.urls import path

from .views import (
    AdminVerificationDecisionView,
    AdminVerificationQueueView,
    BankAccountView,
    CertificateView,
    SubmitVerificationView,
    WorkerDocumentUploadView,
    WorkerMeView,
)

urlpatterns = [
    path("workers/me/", WorkerMeView.as_view(), name="worker-me"),
    path("workers/me/documents/", WorkerDocumentUploadView.as_view(), name="worker-documents"),
    path("workers/me/bank/", BankAccountView.as_view(), name="worker-bank"),
    path("workers/me/certificates/", CertificateView.as_view(), name="worker-certificates"),
    path("workers/me/submit/", SubmitVerificationView.as_view(), name="worker-submit"),
    path("admin/verification/", AdminVerificationQueueView.as_view(), name="admin-verification"),
    path(
        "admin/verification/<uuid:worker_id>/",
        AdminVerificationDecisionView.as_view(),
        name="admin-verification-decision",
    ),
]
