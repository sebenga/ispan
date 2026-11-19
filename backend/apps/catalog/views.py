from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ServiceCategory
from .serializers import ServiceCategorySerializer


class CategoryListView(generics.ListAPIView):
    serializer_class = ServiceCategorySerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return ServiceCategory.objects.filter(is_active=True, parent__isnull=True).prefetch_related(
            "children"
        )


class RateSuggestionView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, slug: str):
        try:
            cat = ServiceCategory.objects.get(slug=slug, is_active=True)
        except ServiceCategory.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)
        return Response(
            {
                "category": cat.slug,
                "city": request.query_params.get("city", "Cape Town"),
                "suggested_min_cents": cat.suggested_min_cents,
                "suggested_max_cents": cat.suggested_max_cents,
                "disclaimer": "Suggested band only — workers set their own rates.",
            }
        )
