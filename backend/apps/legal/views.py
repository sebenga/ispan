from __future__ import annotations

from django.conf import settings
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import LegalConsent

DOCUMENTS = {
    "terms": {
        "title": "Terms of Service",
        "body": (
            "DRAFT — for counsel review.\n\n"
            "iSpan is a marketplace that connects customers with independent contractors "
            "(tradespeople). Workers on iSpan are not employees of iSpan.\n\n"
            "Legal entity: [full legal name]\n"
            "Registration number: [registration number]\n"
            "Directors: [directors]\n"
            "Physical address: [physical address]\n"
            "Postal address: [postal address]\n"
            "Email: [email]\n"
            "Telephone: [telephone]\n"
            "VAT number: [VAT number if registered]\n"
        ),
    },
    "privacy": {
        "title": "Privacy Notice",
        "body": (
            "DRAFT — for counsel review (POPIA).\n\n"
            "Information Officer: [Information Officer name, email, phone]\n\n"
            "We process personal information to operate the marketplace, verify workers, "
            "settle payments, and keep both parties safe. Hosting is on Render in the "
            "Frankfurt region. [cross-border transfer clause]\n\n"
            "Suggested retention starting points (counsel to confirm):\n"
            "- Identity-document images: [90 days after verification, then delete the image "
            "and keep a verification outcome record]\n"
            "- GPS breadcrumbs: [retained only for the job record and a short dispute window]\n"
            "- Chat: [retained for the dispute window, then archived or deleted per policy]\n"
            "- Account data: [for the life of the account plus a legal hold period]\n"
        ),
    },
    "notice": {
        "title": "ECTA Notice",
        "body": (
            "DRAFT — Electronic Communications and Transactions Act notice.\n\n"
            "Full legal name: [full legal name]\n"
            "Registration number: [registration number]\n"
            "Directors: [directors]\n"
            "Physical address: [physical address]\n"
            "Postal address: [postal address]\n"
            "Email: [email]\n"
            "Telephone: [telephone]\n"
            "VAT number: [VAT number if registered]\n"
        ),
    },
}


class LegalVersionView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response(
            {
                "version": settings.LEGAL_VERSION,
                "documents": ["terms", "privacy", "notice"],
                "required_flags": ["age_18", "terms", "privacy"],
            }
        )


class LegalDocumentView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug: str):
        doc = DOCUMENTS.get(slug)
        if not doc:
            return Response({"detail": "Not found.", "code": "not_found"}, status=404)
        return Response(
            {
                "slug": slug,
                "version": settings.LEGAL_VERSION,
                "title": doc["title"],
                "body": doc["body"],
                "draft": True,
            }
        )


class LegalConsentView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        version = request.data.get("version") or settings.LEGAL_VERSION
        flags = request.data.get("flags") or {}
        required = {"age_18", "terms", "privacy"}
        missing = [k for k in required if not flags.get(k)]
        if missing:
            return Response(
                {
                    "detail": "Required acknowledgements are missing.",
                    "code": "consent_incomplete",
                    "missing": missing,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if flags.get("age_18") is not True:
            return Response(
                {
                    "detail": "You must be 18 or over to use iSpan.",
                    "code": "under_age",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        anon_id = request.data.get("anon_id", "")
        ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get(
            "REMOTE_ADDR"
        )
        consent = LegalConsent.objects.create(
            user=request.user if request.user.is_authenticated else None,
            anon_id=anon_id,
            version=version,
            flags=flags,
            ip_address=ip or None,
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:2000],
        )
        return Response(
            {
                "id": str(consent.id),
                "version": consent.version,
                "accepted_at": consent.accepted_at,
            },
            status=status.HTTP_201_CREATED,
        )
