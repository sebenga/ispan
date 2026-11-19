from rest_framework import generics, permissions

from .models import ServiceCategory
from .serializers import ServiceCategorySerializer


class CategoryListView(generics.ListAPIView):
    queryset = ServiceCategory.objects.all()
    serializer_class = ServiceCategorySerializer
    permission_classes = [permissions.AllowAny]
