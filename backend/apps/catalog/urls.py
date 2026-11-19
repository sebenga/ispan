from django.urls import path

from .views import CategoryListView, RateSuggestionView

urlpatterns = [
    path("categories/", CategoryListView.as_view(), name="categories"),
    path(
        "categories/<slug:slug>/rate-suggestion/",
        RateSuggestionView.as_view(),
        name="rate-suggestion",
    ),
]
