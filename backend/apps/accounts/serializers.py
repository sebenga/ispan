from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

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
            "first_name",
            "last_name",
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
        user = User.objects.create_user(password=password, role=role, **validated_data)
        if role == User.Role.WORKER:
            WorkerProfile.objects.create(user=user, city="Cape Town")
        return user


class WorkerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkerProfile
        fields = (
            "id",
            "bio",
            "verification_status",
            "bank_verified",
            "bank_account_masked",
            "hourly_rate_min_cents",
            "is_available",
            "available_from",
            "available_to",
            "service_radius_km",
            "lat",
            "lng",
            "city",
            "avg_rating",
            "rating_count",
            "completed_jobs",
        )
        read_only_fields = (
            "id",
            "verification_status",
            "bank_verified",
            "avg_rating",
            "rating_count",
            "completed_jobs",
        )
