from django.urls import path

from .views import EmergencyContactView

urlpatterns = [
    path("me/emergency-contacts/", EmergencyContactView.as_view(), name="emergency-contacts"),
]
