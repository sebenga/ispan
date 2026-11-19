"""Location, chat, ETA, and SOS domain logic for Phase 3."""

from __future__ import annotations

from apps.common.geo import haversine_km
from apps.core.bus import publish_event
from apps.notifications.services import send_notification
from apps.safety.models import EmergencyContact, SosEvent

from .models import Job, JobEvent, JobTracking, Message
from .services import job_rooms, log_event

# POPIA: precise location only while the job is actively in progress travel/work.
LOCATION_ALLOWED_STATUSES = {
    Job.Status.EN_ROUTE,
    Job.Status.ARRIVED,
    Job.Status.IN_PROGRESS,
}

CHAT_ALLOWED_STATUSES = {
    Job.Status.ACCEPTED,
    Job.Status.EN_ROUTE,
    Job.Status.ARRIVED,
    Job.Status.IN_PROGRESS,
    Job.Status.COMPLETED,
    Job.Status.CONFIRMED,
    Job.Status.DISPUTED,
}

SOS_ALLOWED_STATUSES = {
    Job.Status.ACCEPTED,
    Job.Status.EN_ROUTE,
    Job.Status.ARRIVED,
    Job.Status.IN_PROGRESS,
    Job.Status.COMPLETED,
}

# Assumed urban average speed for ETA (km/h) — not a live traffic feed.
ETA_SPEED_KMH = 25.0


class LocationNotAllowed(Exception):
    code = "location_not_allowed"


class ChatNotAllowed(Exception):
    code = "chat_not_allowed"


def user_can_access_job(user, job: Job) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser or getattr(user, "is_support", False):
        return True
    if job.customer_id == user.id or job.worker_id == user.id:
        return True
    return job.offers.filter(worker_id=user.id).exists()


def estimate_eta_minutes(*, from_lat: float, from_lng: float, to_lat: float, to_lng: float) -> int:
    dist = haversine_km(from_lat, from_lng, to_lat, to_lng)
    if dist <= 0:
        return 0
    minutes = (dist / ETA_SPEED_KMH) * 60
    return max(1, int(round(minutes)))


def record_location(
    *,
    job: Job,
    actor,
    lat: float,
    lng: float,
    accuracy_m: float | None = None,
) -> dict:
    if actor.id != job.worker_id and not (
        actor.is_staff or getattr(actor, "is_support", False)
    ):
        raise PermissionError("Only the assigned worker may send location pings.")
    if job.status not in LOCATION_ALLOWED_STATUSES:
        raise LocationNotAllowed(
            f"Location pings are only allowed during active travel/work "
            f"(en_route, arrived, in_progress). Current status: {job.status}."
        )

    ping = JobTracking.objects.create(
        job=job,
        lat=lat,
        lng=lng,
        accuracy_m=accuracy_m,
        recorded_by=actor,
    )

    eta_minutes = None
    if job.lat is not None and job.lng is not None:
        eta_minutes = estimate_eta_minutes(
            from_lat=lat, from_lng=lng, to_lat=job.lat, to_lng=job.lng
        )

    payload = {
        "job_id": str(job.id),
        "lat": lat,
        "lng": lng,
        "accuracy_m": accuracy_m,
        "recorded_at": ping.recorded_at.isoformat(),
        "eta_minutes": eta_minutes,
        "status": job.status,
    }
    rooms = job_rooms(job) + ["support"]
    publish_event(event="job:location", rooms=rooms, payload=payload)
    if eta_minutes is not None:
        publish_event(
            event="job:eta",
            rooms=rooms,
            payload={"job_id": str(job.id), "eta_minutes": eta_minutes},
        )
    return payload


def latest_location(job: Job) -> dict | None:
    ping = job.tracking.order_by("-recorded_at").first()
    if not ping:
        return None
    eta_minutes = None
    if job.lat is not None and job.lng is not None:
        eta_minutes = estimate_eta_minutes(
            from_lat=ping.lat, from_lng=ping.lng, to_lat=job.lat, to_lng=job.lng
        )
    return {
        "lat": ping.lat,
        "lng": ping.lng,
        "accuracy_m": ping.accuracy_m,
        "recorded_at": ping.recorded_at,
        "eta_minutes": eta_minutes,
    }


def post_chat(*, job: Job, actor, body: str) -> Message:
    body = (body or "").strip()
    if not body:
        raise ValueError("Message body required.")
    if len(body) > 2000:
        raise ValueError("Message too long.")
    if not user_can_access_job(actor, job):
        raise PermissionError("Forbidden")
    if job.status not in CHAT_ALLOWED_STATUSES:
        raise ChatNotAllowed("Chat opens after a job is accepted.")
    if actor.id not in {job.customer_id, job.worker_id} and not (
        actor.is_staff or getattr(actor, "is_support", False)
    ):
        raise PermissionError("Only job parties (or support) may chat.")

    msg = Message.objects.create(job=job, sender=actor, body=body)
    payload = {
        "id": str(msg.id),
        "job_id": str(job.id),
        "sender_id": str(actor.id),
        "sender_name": actor.first_name,
        "body": msg.body,
        "created_at": msg.created_at.isoformat(),
    }
    rooms = job_rooms(job)
    if job.status == Job.Status.DISPUTED:
        rooms.append("support")
    publish_event(event="job:chat", rooms=rooms, payload=payload)
    return msg


def trigger_sos(*, job: Job, actor, lat=None, lng=None, accuracy_m=None, note: str = "") -> SosEvent:
    if not user_can_access_job(actor, job):
        raise PermissionError("Forbidden")
    if actor.id not in {job.customer_id, job.worker_id}:
        raise PermissionError("Only job parties may trigger SOS.")
    if job.status not in SOS_ALLOWED_STATUSES:
        raise ValueError("SOS is only available on an active job.")

    contacts = list(EmergencyContact.objects.filter(user=actor))
    notified = []
    for c in contacts:
        send_notification(
            channel="sms",
            destination=c.phone,
            template="sos_alert",
            body=(
                f"iSpan SOS: {actor.first_name} triggered an emergency alert on a job. "
                f"Approx location: {lat},{lng}. This is NOT a substitute for 10111 / 10177 / 112."
            ),
            subject="iSpan SOS alert",
            user=actor,
            payload={"job_id": str(job.id), "contact": c.name},
        )
        notified.append({"name": c.name, "phone_masked": f"***{c.phone[-3:]}", "channel": "sms"})

    event = SosEvent.objects.create(
        job=job,
        user=actor,
        lat=lat,
        lng=lng,
        accuracy_m=accuracy_m,
        note=note or "",
        notified_parties=notified,
        support_notified=True,
    )
    log_event(
        job,
        "sos",
        actor=actor,
        to_status=job.status,
        sos_id=str(event.id),
    )
    payload = {
        "sos_id": str(event.id),
        "job_id": str(job.id),
        "user_id": str(actor.id),
        "user_name": actor.get_full_name(),
        "lat": lat,
        "lng": lng,
        "created_at": event.created_at.isoformat(),
        "disclaimer": "iSpan SOS alerts support and your emergency contacts. "
        "It does not replace official emergency numbers (police 10111, ambulance 10177, emergency 112).",
    }
    publish_event(
        event="sos:alert",
        rooms=job_rooms(job) + ["support"],
        payload=payload,
    )
    return event


def navigation_links(job: Job) -> dict:
    if job.lat is None or job.lng is None:
        return {"google_maps": None, "waze": None}
    lat, lng = job.lat, job.lng
    return {
        "google_maps": f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}",
        "waze": f"https://waze.com/ul?ll={lat}%2C{lng}&navigate=yes",
    }
