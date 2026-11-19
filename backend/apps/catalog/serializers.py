from rest_framework import serializers

from .models import ServiceCategory, WorkerService


class ServiceCategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    suggested_disclaimer = serializers.SerializerMethodField()

    class Meta:
        model = ServiceCategory
        fields = (
            "id",
            "slug",
            "name",
            "description",
            "parent",
            "icon_key",
            "is_active",
            "min_certificate_types",
            "commission_bps",
            "cancel_fee_bps",
            "cancel_window_minutes",
            "suggested_min_cents",
            "suggested_max_cents",
            "suggested_disclaimer",
            "sort_order",
            "children",
        )

    def get_children(self, obj):
        if self.context.get("flat"):
            return []
        kids = obj.children.filter(is_active=True)
        return ServiceCategorySerializer(kids, many=True, context={"flat": True}).data

    def get_suggested_disclaimer(self, obj):
        return "Suggested band only — workers set their own rates."


class WorkerServiceSerializer(serializers.ModelSerializer):
    category = ServiceCategorySerializer(read_only=True)
    category_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = WorkerService
        fields = ("id", "category", "category_id", "price_cents", "description", "is_active")
