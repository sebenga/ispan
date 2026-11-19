from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.accounts.models import WorkerProfile
from apps.core.models import BaseModel, UUIDModel


class WorkerDocument(BaseModel):
    class DocType(models.TextChoices):
        SA_ID = "sa_id", "South African ID"
        PASSPORT = "passport", "Passport"
        ASYLUM_PERMIT = "asylum_permit", "Asylum seeker permit"
        REFUGEE_ID = "refugee_id", "Refugee ID"
        PROOF_OF_ADDRESS = "proof_of_address", "Proof of address"
        BANK_CONFIRMATION = "bank_confirmation", "Bank confirmation"
        SELFIE = "selfie", "Selfie"

    class ReviewStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        UNSUPPORTED = "UNSUPPORTED", "Cannot verify yet"

    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name="documents")
    doc_type = models.CharField(max_length=32, choices=DocType.choices)
    # Encrypted file bytes stored on disk under private media; path only here.
    storage_path = models.CharField(max_length=512)
    content_type = models.CharField(max_length=120, blank=True)
    size_bytes = models.PositiveIntegerField(default=0)
    review_status = models.CharField(
        max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.PENDING
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_documents",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    # Format-check metadata only — never store raw ID in plain text here.
    id_number_masked = models.CharField(max_length=32, blank=True)
    id_number_encrypted = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]


class BankAccount(BaseModel):
    class VerificationStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        VERIFIED = "VERIFIED", "Verified"
        REJECTED = "REJECTED", "Rejected"

    worker = models.OneToOneField(WorkerProfile, on_delete=models.CASCADE, related_name="bank_account")
    holder_name = models.CharField(max_length=120)
    bank_name = models.CharField(max_length=120)
    account_number_encrypted = models.TextField()
    account_number_masked = models.CharField(max_length=32)
    branch_code = models.CharField(max_length=20, blank=True)
    verification_status = models.CharField(
        max_length=20, choices=VerificationStatus.choices, default=VerificationStatus.PENDING
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_bank_accounts",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)


class Certificate(BaseModel):
    class CertType(models.TextChoices):
        WIREMAN_LICENCE = "wireman_licence", "Wireman's licence"
        ELECTRICAL_COC_AUTHORITY = "electrical_coc_authority", "Electrical CoC authority"
        PIRB = "pirb", "PIRB"
        OTHER = "other", "Other"

    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name="certificates")
    cert_type = models.CharField(max_length=40, choices=CertType.choices)
    number = models.CharField(max_length=120, blank=True)
    issuer = models.CharField(max_length=120, blank=True)
    expires_at = models.DateField(null=True, blank=True)
    storage_path = models.CharField(max_length=512, blank=True)
    verified = models.BooleanField(default=False)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_certificates",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)


class VerificationAudit(UUIDModel):
    """Audit trail for KYC decisions — stores outcomes, not raw secrets."""

    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name="verification_audits")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="verification_actions"
    )
    action = models.CharField(max_length=40)  # submit | approve | reject | document_approve | ...
    outcome = models.CharField(max_length=40, blank=True)
    document_types = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
