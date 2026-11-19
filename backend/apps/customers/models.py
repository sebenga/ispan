from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.core.models import BaseModel


class CustomerProfile(BaseModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="customer_profile"
    )
    photo_url = models.URLField(blank=True)
    billing_preference = models.CharField(max_length=20, default="ESCROW")  # ESCROW | CASH

    def __str__(self) -> str:
        return f"CustomerProfile<{self.user_id}>"


class SavedAddress(BaseModel):
    customer = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE, related_name="addresses")
    label = models.CharField(max_length=80)
    address_line = models.CharField(max_length=255)
    suburb = models.CharField(max_length=120, blank=True)
    city = models.CharField(max_length=80, default="Cape Town")
    region = models.CharField(max_length=80, default="Western Cape")
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)
    access_notes = models.TextField(blank=True)  # personal data — treat carefully
    is_default = models.BooleanField(default=False)
