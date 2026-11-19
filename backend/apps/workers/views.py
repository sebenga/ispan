from __future__ import annotations

from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import WorkerProfile
from apps.accounts.serializers import WorkerProfileSerializer
from apps.common.crypto import encrypt_text
from apps.common.sa_id import is_valid_sa_id, mask_id_number

from .models import BankAccount, Certificate, VerificationAudit, WorkerDocument
from .serializers import BankAccountSerializer, CertificateSerializer, WorkerDocumentSerializer
from .storage import store_encrypted_upload

UNSUPPORTED_ONBOARDING = {WorkerDocument.DocType.ASYLUM_PERMIT, WorkerDocument.DocType.REFUGEE_ID}


def _worker_or_403(request) -> WorkerProfile:
    if not request.user.is_authenticated:
        raise permissions.PermissionDenied()
    profile = getattr(request.user, "worker_profile", None)
    if profile is None:
        raise permissions.PermissionDenied("Workers only.")
    return profile


class WorkerMeView(APIView):
    def get(self, request):
        profile = _worker_or_403(request)
        data = WorkerProfileSerializer(profile).data
        data["documents"] = WorkerDocumentSerializer(profile.documents.all(), many=True).data
        data["certificates"] = CertificateSerializer(profile.certificates.all(), many=True).data
        bank = getattr(profile, "bank_account", None)
        data["bank_account"] = BankAccountSerializer(bank).data if bank else None
        data["checklist"] = {
            "email_verified": request.user.email_verified,
            "phone_verified": request.user.phone_verified,
            "has_photo": bool(request.user.avatar_url),
            "has_id_doc": profile.documents.filter(
                doc_type__in=["sa_id", "passport", "asylum_permit", "refugee_id"]
            ).exists(),
            "has_proof_of_address": profile.documents.filter(doc_type="proof_of_address").exists(),
            "has_bank": bank is not None,
            "has_skill_or_bio": bool(profile.bio) or profile.hourly_rate_min_cents is not None,
        }
        return Response(data)

    def patch(self, request):
        profile = _worker_or_403(request)
        ser = WorkerProfileSerializer(profile, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return self.get(request)


class WorkerDocumentUploadView(APIView):
    def get(self, request):
        profile = _worker_or_403(request)
        return Response(WorkerDocumentSerializer(profile.documents.all(), many=True).data)

    def post(self, request):
        profile = _worker_or_403(request)
        doc_type = request.data.get("doc_type")
        uploaded = request.FILES.get("file")
        if not doc_type or not uploaded:
            return Response(
                {"detail": "doc_type and file are required.", "code": "missing_fields"},
                status=400,
            )
        if doc_type not in WorkerDocument.DocType.values:
            return Response({"detail": "Unknown document type.", "code": "invalid_type"}, status=400)

        id_number = (request.data.get("id_number") or "").strip()
        id_masked = ""
        id_enc = ""
        review_status = WorkerDocument.ReviewStatus.PENDING

        if doc_type in UNSUPPORTED_ONBOARDING:
            # Legal review item: do not silently accept these in MVP.
            review_status = WorkerDocument.ReviewStatus.UNSUPPORTED
        elif doc_type == WorkerDocument.DocType.SA_ID:
            if not id_number or not is_valid_sa_id(id_number):
                return Response(
                    {
                        "detail": "SA ID failed format check (13 digits + checksum). "
                        "This is not a Home Affairs verification.",
                        "code": "invalid_sa_id_format",
                    },
                    status=400,
                )
            id_masked = mask_id_number(id_number)
            id_enc = encrypt_text(id_number)
            profile.id_number_encrypted = id_enc
            profile.id_number_masked = id_masked
            profile.id_document_type = "sa_id"
            profile.save(
                update_fields=[
                    "id_number_encrypted",
                    "id_number_masked",
                    "id_document_type",
                    "updated_at",
                ]
            )
        elif doc_type == WorkerDocument.DocType.PASSPORT and id_number:
            id_masked = mask_id_number(id_number) if id_number.isdigit() else f"***{id_number[-4:]}"
            id_enc = encrypt_text(id_number)
            profile.id_number_encrypted = id_enc
            profile.id_number_masked = id_masked
            profile.id_document_type = "passport"
            profile.save(
                update_fields=[
                    "id_number_encrypted",
                    "id_number_masked",
                    "id_document_type",
                    "updated_at",
                ]
            )

        try:
            path, content_type, size = store_encrypted_upload(
                worker_id=profile.id, doc_type=doc_type, uploaded=uploaded
            )
        except ValueError as exc:
            return Response({"detail": str(exc), "code": "upload_rejected"}, status=400)

        doc = WorkerDocument.objects.create(
            worker=profile,
            doc_type=doc_type,
            storage_path=path,
            content_type=content_type,
            size_bytes=size,
            review_status=review_status,
            id_number_masked=id_masked,
            id_number_encrypted=id_enc,
            notes=(
                "Document type flagged for legal review — cannot verify yet."
                if review_status == WorkerDocument.ReviewStatus.UNSUPPORTED
                else ""
            ),
        )
        return Response(WorkerDocumentSerializer(doc).data, status=201)


class BankAccountView(APIView):
    def get(self, request):
        profile = _worker_or_403(request)
        bank = getattr(profile, "bank_account", None)
        return Response(BankAccountSerializer(bank).data if bank else None)

    def put(self, request):
        profile = _worker_or_403(request)
        holder = request.data.get("holder_name")
        bank_name = request.data.get("bank_name")
        account_number = (request.data.get("account_number") or "").strip()
        branch = request.data.get("branch_code", "")
        if not holder or not bank_name or not account_number:
            return Response({"detail": "holder_name, bank_name and account_number required."}, status=400)
        masked = f"****{account_number[-4:]}" if len(account_number) >= 4 else "****"
        bank, _ = BankAccount.objects.update_or_create(
            worker=profile,
            defaults={
                "holder_name": holder,
                "bank_name": bank_name,
                "account_number_encrypted": encrypt_text(account_number),
                "account_number_masked": masked,
                "branch_code": branch,
                "verification_status": BankAccount.VerificationStatus.PENDING,
            },
        )
        profile.bank_account_masked = masked
        profile.bank_verified = False
        profile.save(update_fields=["bank_account_masked", "bank_verified", "updated_at"])
        return Response(BankAccountSerializer(bank).data)


class CertificateView(APIView):
    def get(self, request):
        profile = _worker_or_403(request)
        return Response(CertificateSerializer(profile.certificates.all(), many=True).data)

    def post(self, request):
        profile = _worker_or_403(request)
        cert_type = request.data.get("cert_type")
        if cert_type not in Certificate.CertType.values:
            return Response({"detail": "Invalid cert_type."}, status=400)
        uploaded = request.FILES.get("file")
        storage_path = ""
        if uploaded:
            try:
                storage_path, _, _ = store_encrypted_upload(
                    worker_id=profile.id, doc_type=f"cert_{cert_type}", uploaded=uploaded
                )
            except ValueError as exc:
                return Response({"detail": str(exc)}, status=400)
        cert = Certificate.objects.create(
            worker=profile,
            cert_type=cert_type,
            number=request.data.get("number", ""),
            issuer=request.data.get("issuer", ""),
            expires_at=request.data.get("expires_at") or None,
            storage_path=storage_path,
        )
        return Response(CertificateSerializer(cert).data, status=201)


class SubmitVerificationView(APIView):
    def post(self, request):
        profile = _worker_or_403(request)
        if not request.user.email_verified or not request.user.phone_verified:
            return Response(
                {
                    "detail": "Verify email and phone before submitting for review.",
                    "code": "otp_required",
                },
                status=400,
            )
        has_id = profile.documents.filter(
            doc_type__in=["sa_id", "passport"],
            review_status__in=["PENDING", "APPROVED"],
        ).exists()
        if not has_id:
            return Response(
                {
                    "detail": "Upload a South African ID or passport before submitting.",
                    "code": "id_required",
                },
                status=400,
            )
        if not getattr(profile, "bank_account", None):
            return Response({"detail": "Add bank details before submitting.", "code": "bank_required"}, status=400)

        profile.verification_status = WorkerProfile.VerificationStatus.SUBMITTED
        profile.submitted_at = timezone.now()
        profile.rejection_reason = ""
        profile.save(update_fields=["verification_status", "submitted_at", "rejection_reason", "updated_at"])
        VerificationAudit.objects.create(
            worker=profile,
            actor=request.user,
            action="submit",
            outcome="submitted",
            document_types=list(profile.documents.values_list("doc_type", flat=True)),
        )
        return Response(WorkerProfileSerializer(profile).data)


class IsStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (request.user.is_staff or request.user.is_support or request.user.is_superuser)
        )


class AdminVerificationQueueView(APIView):
    permission_classes = [IsStaff]

    def get(self, request):
        qs = WorkerProfile.objects.filter(
            verification_status__in=[
                WorkerProfile.VerificationStatus.SUBMITTED,
                WorkerProfile.VerificationStatus.PENDING,
            ]
        ).select_related("user")
        rows = []
        for p in qs:
            rows.append(
                {
                    "id": str(p.id),
                    "user_id": str(p.user_id),
                    "name": p.display_name or p.user.get_full_name(),
                    "email": p.user.email,
                    "phone": p.user.phone,
                    "verification_status": p.verification_status,
                    "id_number_masked": p.id_number_masked,
                    "id_document_type": p.id_document_type,
                    "bank_account_masked": p.bank_account_masked,
                    "submitted_at": p.submitted_at,
                    "documents": WorkerDocumentSerializer(p.documents.all(), many=True).data,
                    "certificates": CertificateSerializer(p.certificates.all(), many=True).data,
                }
            )
        return Response({"results": rows})


class AdminVerificationDecisionView(APIView):
    permission_classes = [IsStaff]

    def post(self, request, worker_id):
        try:
            profile = WorkerProfile.objects.select_related("user").get(id=worker_id)
        except WorkerProfile.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)

        decision = request.data.get("decision")  # approve | reject
        reason = request.data.get("reason", "")
        if decision not in ("approve", "reject"):
            return Response({"detail": "decision must be approve or reject."}, status=400)
        if decision == "reject" and not reason:
            return Response({"detail": "Rejection reason is required."}, status=400)

        if decision == "approve":
            profile.verification_status = WorkerProfile.VerificationStatus.VERIFIED
            profile.rejection_reason = ""
            profile.bank_verified = True
            if hasattr(profile, "bank_account") and profile.bank_account:
                profile.bank_account.verification_status = BankAccount.VerificationStatus.VERIFIED
                profile.bank_account.reviewed_by = request.user
                profile.bank_account.reviewed_at = timezone.now()
                profile.bank_account.save()
            profile.documents.exclude(review_status=WorkerDocument.ReviewStatus.UNSUPPORTED).update(
                review_status=WorkerDocument.ReviewStatus.APPROVED,
                reviewed_by=request.user,
                reviewed_at=timezone.now(),
            )
            profile.certificates.update(verified=True, reviewed_by=request.user, reviewed_at=timezone.now())
        else:
            profile.verification_status = WorkerProfile.VerificationStatus.REJECTED
            profile.rejection_reason = reason
            profile.bank_verified = False

        profile.reviewed_by = request.user
        profile.reviewed_at = timezone.now()
        profile.save()

        VerificationAudit.objects.create(
            worker=profile,
            actor=request.user,
            action=decision,
            outcome=profile.verification_status,
            document_types=list(profile.documents.values_list("doc_type", flat=True)),
            notes=reason,
        )
        return Response(WorkerProfileSerializer(profile).data)
