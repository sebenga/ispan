from django.urls import path

from .views import LegalConsentView, LegalDocumentView, LegalVersionView

urlpatterns = [
    path("version/", LegalVersionView.as_view(), name="legal-version"),
    path("documents/<slug:slug>/", LegalDocumentView.as_view(), name="legal-document"),
    path("consent/", LegalConsentView.as_view(), name="legal-consent"),
]
