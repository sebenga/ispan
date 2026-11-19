from rest_framework import serializers

from .models import ServiceCategory, WorkerService


class ServiceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = (
            "id",
            "slug",
            "name",
            "description",
            "suggested_min_cents",
            "suggested_max_cents",
        )


class WorkerServiceSerializer(serializers.ModelSerializer):
    category = ServiceCategorySerializer(read_only=True)
    category_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = WorkerService
        fields = ("id", "category", "category_id", "price_cents", "description")
