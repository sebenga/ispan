from __future__ import annotations

from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.catalog.serializers import ServiceCategorySerializer
from apps.payments.models import Payment, PaymentLedger

from .models import Job, Rating


class PaymentLedgerSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentLedger
        fields = ("id", "event", "amount_cents", "meta", "created_at")


class PaymentSerializer(serializers.ModelSerializer):
    ledger = PaymentLedgerSerializer(many=True, read_only=True)

    class Meta:
        model = Payment
        fields = (
            "id",
            "method",
            "status",
            "amount_cents",
            "commission_cents",
            "worker_payout_cents",
            "provider",
            "provider_ref",
            "held_at",
            "released_at",
            "refunded_at",
            "ledger",
        )


class JobSerializer(serializers.ModelSerializer):
    category = ServiceCategorySerializer(read_only=True)
    customer = UserSerializer(read_only=True)
    worker = UserSerializer(read_only=True)
    payment = PaymentSerializer(read_only=True)

    class Meta:
        model = Job
        fields = (
            "id",
            "title",
            "description",
            "status",
            "payment_method",
            "budget_cents",
            "agreed_price_cents",
            "commission_bps",
            "scheduled_at",
            "is_immediate",
            "address_line",
            "suburb",
            "city",
            "lat",
            "lng",
            "started_at",
            "completed_at",
            "created_at",
            "category",
            "customer",
            "worker",
            "payment",
        )


class JobCreateSerializer(serializers.Serializer):
    category_id = serializers.UUIDField()
    title = serializers.CharField(max_length=160)
    description = serializers.CharField()
    payment_method = serializers.ChoiceField(choices=["ESCROW", "CASH"])
    budget_cents = serializers.IntegerField(min_value=1000)
    scheduled_at = serializers.DateTimeField(required=False, allow_null=True)
    is_immediate = serializers.BooleanField(default=True)
    address_line = serializers.CharField(max_length=255)
    suburb = serializers.CharField(max_length=120)
    city = serializers.CharField(max_length=80, default="Cape Town")
    lat = serializers.FloatField(required=False, allow_null=True)
    lng = serializers.FloatField(required=False, allow_null=True)


class RatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rating
        fields = ("id", "score", "comment", "from_user", "to_user", "created_at")
        read_only_fields = fields


class RatingCreateSerializer(serializers.Serializer):
    score = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(required=False, allow_blank=True, max_length=1000)
