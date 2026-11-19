from __future__ import annotations

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.customers.models import CustomerProfile, SavedAddress
from apps.legal.models import LegalConsent

from .models import WorkerProfile
from .otp import request_otp, verify_otp
from .serializers import RegisterSerializer, UserSerializer, WorkerProfileSerializer
from .tokens import EmailTokenObtainPairSerializer

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Persist legal consent if provided at signup
        flags = request.data.get("consent_flags") or {}
        version = request.data.get("consent_version") or settings.LEGAL_VERSION
        if flags.get("age_18") and flags.get("terms") and flags.get("privacy"):
            LegalConsent.objects.create(
                user=user,
                version=version,
                flags=flags,
                ip_address=request.META.get("REMOTE_ADDR"),
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:2000],
            )

        # Kick off OTPs (mock)
        request_otp(purpose="signup_email", destination=user.email, user=user, channel="email")
        request_otp(purpose="signup_phone", destination=user.phone, user=user, channel="sms")

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "user": UserSerializer(user).data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "otp": {
                    "email_sent": True,
                    "phone_sent": True,
                    "hint": "In mock/DEBUG mode the code is 123456 (see mock inbox).",
                },
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    permission_classes = [permissions.AllowAny]
    serializer_class = EmailTokenObtainPairSerializer


class LogoutView(APIView):
    def post(self, request):
        # Client discards tokens; blacklist can be added later.
        return Response({"detail": "Logged out."})


class MeView(APIView):
    def get(self, request):
        data = UserSerializer(request.user).data
        if request.user.is_worker or hasattr(request.user, "worker_profile"):
            profile = getattr(request.user, "worker_profile", None)
            data["worker_profile"] = WorkerProfileSerializer(profile).data if profile else None
        if hasattr(request.user, "customer_profile"):
            data["customer_profile"] = {
                "id": str(request.user.customer_profile.id),
                "billing_preference": request.user.customer_profile.billing_preference,
            }
        return Response(data)

    def patch(self, request):
        user = request.user
        for field in ("first_name", "last_name", "preferred_language", "avatar_url", "active_profile"):
            if field in request.data:
                setattr(user, field, request.data[field])
        if "active_profile" in request.data:
            active = request.data["active_profile"]
            if active == "WORKER" and not user.is_worker:
                return Response({"detail": "No worker profile.", "code": "no_worker"}, status=400)
            if active == "CUSTOMER" and not user.is_customer:
                return Response({"detail": "No customer profile.", "code": "no_customer"}, status=400)
            user.role = active
        user.save()
        return self.get(request)


class OtpRequestView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        purpose = request.data.get("purpose")
        destination = request.data.get("destination")
        if purpose not in {c.value for c in __import__("apps.accounts.models", fromlist=["OtpChallenge"]).OtpChallenge.Purpose}:
            return Response({"detail": "Invalid purpose.", "code": "invalid_purpose"}, status=400)
        if not destination:
            return Response({"detail": "destination required.", "code": "missing_destination"}, status=400)
        channel = "email" if "@" in destination else "sms"
        user = request.user if request.user.is_authenticated else None
        challenge, _code = request_otp(
            purpose=purpose, destination=destination, user=user, channel=channel
        )
        return Response(
            {
                "id": str(challenge.id),
                "expires_at": challenge.expires_at,
                "hint": "Mock/DEBUG code is 123456." if settings.DEBUG else "Code sent.",
            }
        )


class OtpVerifyView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        purpose = request.data.get("purpose")
        destination = request.data.get("destination")
        code = request.data.get("code", "")
        try:
            challenge = verify_otp(purpose=purpose, destination=destination, code=code)
        except ValueError as exc:
            return Response({"detail": str(exc), "code": "otp_invalid"}, status=400)

        user = challenge.user
        if user is None and request.user.is_authenticated:
            user = request.user
        if user is None:
            user = User.objects.filter(email__iexact=destination).first() or User.objects.filter(
                phone=destination
            ).first()

        if user:
            if purpose in ("signup_email", "email_change") or "@" in destination:
                user.email_verified = True
            if purpose in ("signup_phone", "phone_change") or destination.startswith("+"):
                user.phone_verified = True
            # Also mark by destination match
            if destination.lower() == user.email.lower():
                user.email_verified = True
            if destination == user.phone:
                user.phone_verified = True
            user.save()
            challenge.user = user
            challenge.save(update_fields=["user"])

        return Response(
            {
                "detail": "Verified.",
                "email_verified": getattr(user, "email_verified", None),
                "phone_verified": getattr(user, "phone_verified", None),
            }
        )


class EnableWorkerProfileView(APIView):
    """Allow a customer account to also become a worker (role switcher)."""

    def post(self, request):
        user = request.user
        profile, _ = WorkerProfile.objects.get_or_create(
            user=user,
            defaults={
                "city": "Cape Town",
                "display_name": f"{user.first_name} {user.last_name}".strip(),
            },
        )
        user.is_worker = True
        user.save(update_fields=["is_worker"])
        return Response(WorkerProfileSerializer(profile).data, status=201)


class WorkerProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = WorkerProfileSerializer

    def get_object(self):
        if not (self.request.user.is_worker or hasattr(self.request.user, "worker_profile")):
            raise permissions.PermissionDenied("Workers only.")
        profile, _ = WorkerProfile.objects.get_or_create(
            user=self.request.user,
            defaults={
                "city": "Cape Town",
                "display_name": f"{self.request.user.first_name} {self.request.user.last_name}".strip(),
            },
        )
        return profile


class CustomerProfileView(APIView):
    def get(self, request):
        profile, _ = CustomerProfile.objects.get_or_create(user=request.user)
        addresses = [
            {
                "id": str(a.id),
                "label": a.label,
                "address_line": a.address_line,
                "suburb": a.suburb,
                "city": a.city,
                "is_default": a.is_default,
            }
            for a in profile.addresses.all()
        ]
        return Response(
            {
                "id": str(profile.id),
                "billing_preference": profile.billing_preference,
                "addresses": addresses,
            }
        )

    def patch(self, request):
        profile, _ = CustomerProfile.objects.get_or_create(user=request.user)
        if "billing_preference" in request.data:
            profile.billing_preference = request.data["billing_preference"]
            profile.save(update_fields=["billing_preference", "updated_at"])
        return self.get(request)


class SavedAddressView(APIView):
    def post(self, request):
        profile, _ = CustomerProfile.objects.get_or_create(user=request.user)
        addr = SavedAddress.objects.create(
            customer=profile,
            label=request.data.get("label", "Home"),
            address_line=request.data["address_line"],
            suburb=request.data.get("suburb", ""),
            city=request.data.get("city", "Cape Town"),
            region=request.data.get("region", "Western Cape"),
            lat=request.data.get("lat"),
            lng=request.data.get("lng"),
            access_notes=request.data.get("access_notes", ""),
            is_default=bool(request.data.get("is_default", False)),
        )
        return Response({"id": str(addr.id)}, status=201)
