from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        # Case-insensitive email login (USERNAME_FIELD lookups are exact-match).
        raw = attrs.get(self.username_field)
        if isinstance(raw, str):
            attrs[self.username_field] = raw.strip().lower()

        data = super().validate(attrs)
        if self.user.is_suspended:
            raise serializers.ValidationError("Account suspended.")
        data["user"] = {
            "id": str(self.user.id),
            "email": self.user.email,
            "phone": self.user.phone,
            "role": self.user.role,
            "is_customer": self.user.is_customer,
            "is_worker": self.user.is_worker,
            "is_support": self.user.is_support,
            "active_profile": self.user.active_profile,
            "first_name": self.user.first_name,
            "last_name": self.user.last_name,
            "email_verified": self.user.email_verified,
            "phone_verified": self.user.phone_verified,
        }
        return data
