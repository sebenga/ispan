from __future__ import annotations

from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.catalog.serializers import ServiceCategorySerializer

from .cancellation import build_cancellation_policy_text
from .models import Job, JobOffer, Quote, Rating


class JobOfferSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobOffer
        fields = (
            "id",
            "job",
            "worker",
            "status",
            "distance_km",
            "notified_at",
            "expires_at",
            "seen_at",
            "responded_at",
        )
        read_only_fields = fields


class QuoteSerializer(serializers.ModelSerializer):
    actor = UserSerializer(read_only=True)

    class Meta:
        model = Quote
        fields = ("id", "job", "actor", "amount_cents", "message", "status", "created_at")
        read_only_fields = fields


class JobSerializer(serializers.ModelSerializer):
    category = ServiceCategorySerializer(read_only=True)
    customer = UserSerializer(read_only=True)
    worker = UserSerializer(read_only=True)
    offers = JobOfferSerializer(many=True, read_only=True)
    quotes = QuoteSerializer(many=True, read_only=True)
    cancellation_policy = serializers.SerializerMethodField()
    pins = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = (
            "id",
            "title",
            "description",
            "status",
            "mode",
            "payment_method",
            "currency",
            "budget_cents",
            "agreed_price_cents",
            "commission_bps",
            "cancel_fee_bps",
            "cancel_window_minutes",
            "cancellation_policy_text",
            "cancellation_policy",
            "cancellation_fee_cents",
            "cancellation_snapshot",
            "scheduled_at",
            "is_immediate",
            "address_line",
            "suburb",
            "city",
            "region",
            "lat",
            "lng",
            "women_preferred",
            "match_radius_km",
            "match_round",
            "accepted_at",
            "started_at",
            "completed_at",
            "confirmed_at",
            "created_at",
            "category",
            "customer",
            "worker",
            "offers",
            "quotes",
            "pins",
        )

    def get_cancellation_policy(self, obj: Job) -> dict:
        return {
            "text": obj.cancellation_policy_text
            or build_cancellation_policy_text(
                fee_bps=obj.cancel_fee_bps, window_minutes=obj.cancel_window_minutes
            ),
            "fee_bps": obj.cancel_fee_bps,
            "window_minutes": obj.cancel_window_minutes,
        }

    def get_pins(self, obj: Job):
        # PINs are only attached when the view sets request context plaintext once.
        return self.context.get("pins")


class JobCreateSerializer(serializers.Serializer):
    category_id = serializers.UUIDField()
    title = serializers.CharField(max_length=160)
    description = serializers.CharField()
    payment_method = serializers.ChoiceField(choices=["ESCROW", "CASH"])
    budget_cents = serializers.IntegerField(min_value=1000, required=False, allow_null=True)
    scheduled_at = serializers.DateTimeField(required=False, allow_null=True)
    is_immediate = serializers.BooleanField(default=True)
    mode = serializers.ChoiceField(choices=["instant", "scheduled"], required=False)
    address_line = serializers.CharField(max_length=255)
    suburb = serializers.CharField(max_length=120)
    city = serializers.CharField(max_length=80, default="Cape Town")
    region = serializers.CharField(max_length=80, default="Western Cape", required=False)
    lat = serializers.FloatField(required=False, allow_null=True)
    lng = serializers.FloatField(required=False, allow_null=True)
    women_preferred = serializers.BooleanField(default=False)
    accept_cancellation_policy = serializers.BooleanField()

    def validate(self, attrs):
        if not attrs.get("accept_cancellation_policy"):
            raise serializers.ValidationError(
                {
                    "accept_cancellation_policy": "You must acknowledge the cancellation policy.",
                    "code": "policy_required",
                }
            )
        mode = attrs.get("mode")
        if not mode:
            mode = "instant" if attrs.get("is_immediate", True) else "scheduled"
            attrs["mode"] = mode
        if mode == "scheduled" and not attrs.get("scheduled_at"):
            raise serializers.ValidationError({"scheduled_at": "Scheduled jobs need a start time."})
        return attrs


class RatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rating
        fields = ("id", "score", "comment", "from_user", "to_user", "created_at")
        read_only_fields = fields


class RatingCreateSerializer(serializers.Serializer):
    score = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(required=False, allow_blank=True, max_length=1000)


class QuoteCreateSerializer(serializers.Serializer):
    amount_cents = serializers.IntegerField(min_value=1000)
    message = serializers.CharField(required=False, allow_blank=True, max_length=1000)
