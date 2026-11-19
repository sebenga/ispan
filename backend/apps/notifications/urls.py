from django.urls import path

from .views import MockInboxView

urlpatterns = [
    path("notifications/mock-inbox/", MockInboxView.as_view(), name="mock-inbox"),
]
