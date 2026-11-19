"""Internal endpoints for the Node realtime gateway (shared secret)."""

from __future__ import annotations

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.jobs.models import Job
from apps.jobs.realtime import user_can_access_job

User = get_user_model()


def _token_ok(request) -> bool:
    header = request.headers.get("X-Internal-Token") or request.META.get("HTTP_X_INTERNAL_TOKEN")
    return bool(header) and header == settings.INTERNAL_API_TOKEN


class RealtimeAuthorizeView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        if not _token_ok(request):
            return Response({"detail": "Unauthorized.", "code": "internal_auth"}, status=401)

        user_id = request.data.get("user_id")
        room = request.data.get("room", "")
        if not user_id or not room:
            return Response({"detail": "user_id and room required."}, status=400)

        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"allowed": False, "reason": "user_not_found"})

        if room == f"user:{user_id}":
            return Response({"allowed": True, "room": room})
        if room == "support":
            allowed = bool(user.is_staff or user.is_superuser or getattr(user, "is_support", False))
            return Response({"allowed": allowed, "room": room})

        if room.startswith("job:"):
            job_id = room.split(":", 1)[1]
            try:
                job = Job.objects.get(id=job_id)
            except (Job.DoesNotExist, ValueError):
                return Response({"allowed": False, "reason": "job_not_found"})
            return Response({"allowed": user_can_access_job(user, job), "room": room})

        return Response({"allowed": False, "reason": "unknown_room"})
