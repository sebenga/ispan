from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from apps.customers.models import CustomerProfile

from .models import WorkerProfile

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "phone",
            "role",
            "is_customer",
            "is_worker",
            "is_support",
            "active_profile",
            "first_name",
            "last_name",
            "preferred_language",
            "avatar_url",
            "email_verified",
            "phone_verified",
        )
        read_only_fields = fields


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20)
    password = serializers.CharField(min_length=8, write_only=True)
    first_name = serializers.CharField(max_length=80)
    last_name = serializers.CharField(max_length=80)
    role = serializers.ChoiceField(choices=["CUSTOMER", "WORKER"])
    preferred_language = serializers.ChoiceField(
        choices=["en", "xh", "af", "zu"], default="en", required=False
    )
    consent_version = serializers.CharField(required=False, allow_blank=True)
    consent_flags = serializers.DictField(required=False)

    def validate_email(self, value: str) -> str:
        email = value.lower().strip()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("Email already registered.")
        return email

    def validate_phone(self, value: str) -> str:
        if User.objects.filter(phone=value).exists():
            raise serializers.ValidationError("Phone already registered.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        role = validated_data.pop("role")
        password = validated_data.pop("password")
        validated_data.pop("consent_version", None)
        validated_data.pop("consent_flags", None)
        lang = validated_data.pop("preferred_language", "en")

        user = User.objects.create_user(
            password=password,
            role=role,
            active_profile=role,
            is_customer=role == "CUSTOMER",
            is_worker=role == "WORKER",
            preferred_language=lang,
            **validated_data,
        )
        if role == "WORKER":
            WorkerProfile.objects.create(
                user=user,
                city="Cape Town",
                display_name=f"{user.first_name} {user.last_name}".strip(),
            )
            user.is_customer = True  # dual-profile ready; customer profile optional
            user.save(update_fields=["is_customer"])
        CustomerProfile.objects.get_or_create(user=user)
        if role == "CUSTOMER":
            user.is_customer = True
            user.save(update_fields=["is_customer"])
        return user


class WorkerProfileSerializer(serializers.ModelSerializer):
    can_receive_payouts = serializers.BooleanField(read_only=True)

    class Meta:
        model = WorkerProfile
        fields = (
            "id",
            "display_name",
            "bio",
            "years_experience",
            "verification_status",
            "rejection_reason",
            "bank_verified",
            "bank_account_masked",
            "id_number_masked",
            "id_document_type",
            "hourly_rate_min_cents",
            "is_available",
            "available_from",
            "available_to",
            "service_radius_km",
            "lat",
            "lng",
            "city",
            "region",
            "country",
            "women_preferred_opt_in",
            "avg_rating",
            "rating_count",
            "completed_jobs",
            "submitted_at",
            "reviewed_at",
            "can_receive_payouts",
        )
        read_only_fields = (
            "id",
            "verification_status",
            "rejection_reason",
            "bank_verified",
            "bank_account_masked",
            "id_number_masked",
            "avg_rating",
            "rating_count",
            "completed_jobs",
            "submitted_at",
            "reviewed_at",
            "can_receive_payouts",
        )
