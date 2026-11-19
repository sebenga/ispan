from rest_framework import serializers

from .models import BankAccount, Certificate, WorkerDocument


class WorkerDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkerDocument
        fields = (
            "id",
            "doc_type",
            "content_type",
            "size_bytes",
            "review_status",
            "notes",
            "id_number_masked",
            "created_at",
            "reviewed_at",
        )
        read_only_fields = fields


class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = (
            "id",
            "holder_name",
            "bank_name",
            "account_number_masked",
            "branch_code",
            "verification_status",
            "notes",
            "reviewed_at",
        )
        read_only_fields = fields


class CertificateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Certificate
        fields = (
            "id",
            "cert_type",
            "number",
            "issuer",
            "expires_at",
            "verified",
            "notes",
            "reviewed_at",
        )
        read_only_fields = fields
