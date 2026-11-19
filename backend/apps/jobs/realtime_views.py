from __future__ import annotations

from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Job, JobEvent
from .realtime import (
    ChatNotAllowed,
    LocationNotAllowed,
    latest_location,
    navigation_links,
    post_chat,
    record_location,
    trigger_sos,
    user_can_access_job,
)


class JobChatView(APIView):
    def get(self, request, job_id):
        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)
        if not user_can_access_job(request.user, job):
            return Response({"detail": "Forbidden."}, status=403)
        rows = [
            {
                "id": str(m.id),
                "sender_id": str(m.sender_id),
                "sender_name": m.sender.first_name,
                "body": m.body,
                "created_at": m.created_at,
            }
            for m in job.messages.select_related("sender").all()
        ]
        return Response({"results": rows})

    def post(self, request, job_id):
        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)
        try:
            msg = post_chat(job=job, actor=request.user, body=request.data.get("body", ""))
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=403)
        except ChatNotAllowed as exc:
            return Response({"detail": str(exc), "code": exc.code}, status=409)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(
            {
                "id": str(msg.id),
                "sender_id": str(msg.sender_id),
                "sender_name": request.user.first_name,
                "body": msg.body,
                "created_at": msg.created_at,
            },
            status=201,
        )


class JobLocationView(APIView):
    def get(self, request, job_id):
        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)
        if not user_can_access_job(request.user, job):
            return Response({"detail": "Forbidden."}, status=403)
        return Response(
            {
                "latest": latest_location(job),
                "navigation": navigation_links(job),
                "allowed_statuses": sorted(
                    ["EN_ROUTE", "ARRIVED", "IN_PROGRESS"]
                ),
            }
        )

    def post(self, request, job_id):
        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)
        lat = request.data.get("lat")
        lng = request.data.get("lng")
        if lat is None or lng is None:
            return Response({"detail": "lat and lng required.", "code": "missing_coords"}, status=400)
        try:
            payload = record_location(
                job=job,
                actor=request.user,
                lat=float(lat),
                lng=float(lng),
                accuracy_m=request.data.get("accuracy_m"),
            )
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=403)
        except LocationNotAllowed as exc:
            return Response({"detail": str(exc), "code": exc.code}, status=409)
        return Response(payload, status=201)


class JobSosView(APIView):
    def post(self, request, job_id):
        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)
        try:
            event = trigger_sos(
                job=job,
                actor=request.user,
                lat=request.data.get("lat"),
                lng=request.data.get("lng"),
                accuracy_m=request.data.get("accuracy_m"),
                note=request.data.get("note", ""),
            )
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=403)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=409)
        return Response(
            {
                "id": str(event.id),
                "status": event.status,
                "notified_parties": event.notified_parties,
                "disclaimer": (
                    "iSpan SOS alerts support and your emergency contacts. "
                    "It does not replace official emergency numbers "
                    "(police 10111, ambulance 10177, emergency 112)."
                ),
                "created_at": event.created_at,
            },
            status=201,
        )


class JobEventsView(APIView):
    def get(self, request, job_id):
        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)
        if not user_can_access_job(request.user, job):
            return Response({"detail": "Forbidden."}, status=403)
        rows = [
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "from_status": e.from_status,
                "to_status": e.to_status,
                "metadata": e.metadata,
                "created_at": e.created_at,
            }
            for e in JobEvent.objects.filter(job=job)
        ]
        return Response({"results": rows})


class JobNavigationView(APIView):
    def get(self, request, job_id):
        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)
        if not user_can_access_job(request.user, job):
            return Response({"detail": "Forbidden."}, status=403)
        return Response(navigation_links(job))
