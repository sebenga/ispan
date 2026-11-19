from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import WorkerProfile
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
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(TokenObtainPairView):
    permission_classes = [permissions.AllowAny]
    serializer_class = EmailTokenObtainPairSerializer


class MeView(APIView):
    def get(self, request):
        data = UserSerializer(request.user).data
        if request.user.role == User.Role.WORKER:
            profile = getattr(request.user, "worker_profile", None)
            data["worker_profile"] = (
                WorkerProfileSerializer(profile).data if profile else None
            )
        return Response(data)


class WorkerProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = WorkerProfileSerializer

    def get_object(self):
        if self.request.user.role != User.Role.WORKER:
            raise permissions.PermissionDenied("Workers only.")
        profile, _ = WorkerProfile.objects.get_or_create(
            user=self.request.user, defaults={"city": "Cape Town"}
        )
        return profile
