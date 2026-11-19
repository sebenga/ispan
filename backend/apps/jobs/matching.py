"""Server-side matching: radius, certificates, availability, offer broadcast."""

from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import WorkerProfile
from apps.catalog.models import WorkerService
from apps.common.geo import bounding_box, haversine_km
from apps.core.bus import publish_event
from apps.scheduling.models import get_matching_config
from apps.workers.models import Certificate

from .models import Job, JobEvent, JobOffer


def _category_ids(category) -> set:
    ids = {category.id}
    # Include parent and children so skills on either side match.
    if category.parent_id:
        ids.add(category.parent_id)
    ids.update(category.children.values_list("id", flat=True))
    return ids


def worker_has_required_certs(profile: WorkerProfile, required: list[str]) -> bool:
    if not required:
        return True
    have = set(
        Certificate.objects.filter(worker=profile, verified=True, cert_type__in=required).values_list(
            "cert_type", flat=True
        )
    )
    return set(required).issubset(have)


def find_candidates(job: Job, *, radius_km: float | None = None) -> list[tuple[WorkerProfile, float]]:
    if job.lat is None or job.lng is None:
        return []

    cfg = get_matching_config()
    radius = radius_km if radius_km is not None else job.match_radius_km or cfg.initial_radius_km
    cat_ids = _category_ids(job.category)
    required = list(job.category.min_certificate_types or [])

    min_lat, max_lat, min_lng, max_lng = bounding_box(job.lat, job.lng, radius)
    qs = (
        WorkerProfile.objects.select_related("user")
        .filter(
            verification_status=WorkerProfile.VerificationStatus.VERIFIED,
            lat__gte=min_lat,
            lat__lte=max_lat,
            lng__gte=min_lng,
            lng__lte=max_lng,
            user__is_active=True,
            user__is_worker=True,
        )
        .exclude(user_id=job.customer_id)
    )
    if job.mode == Job.Mode.INSTANT or job.is_immediate:
        qs = qs.filter(is_available=True)
    if job.women_preferred:
        qs = qs.filter(women_preferred_opt_in=True)
    if cfg.rating_floor:
        qs = qs.filter(Q(rating_count=0) | Q(avg_rating__gte=cfg.rating_floor))

    skilled = set(
        WorkerService.objects.filter(
            category_id__in=cat_ids, is_active=True, worker_id__in=qs.values_list("id", flat=True)
        ).values_list("worker_id", flat=True)
    )
    # Already offered / declined this job in an active or terminal way this round?
    already = set(
        JobOffer.objects.filter(job=job)
        .exclude(status=JobOffer.Status.EXPIRED)
        .values_list("worker_id", flat=True)
    )

    results: list[tuple[WorkerProfile, float]] = []
    for profile in qs:
        if profile.id not in skilled:
            continue
        if profile.user_id in already:
            continue
        if profile.user.is_suspended:
            continue
        if not worker_has_required_certs(profile, required):
            continue
        dist = haversine_km(job.lat, job.lng, profile.lat, profile.lng)
        if dist > radius:
            continue
        if profile.service_radius_km and dist > profile.service_radius_km:
            continue
        results.append((profile, dist))

    results.sort(key=lambda x: (x[1], -(x[0].avg_rating or 0)))
    return results[: cfg.max_concurrent_offers]


@transaction.atomic
def broadcast_offers(job: Job, *, widen: bool = False) -> list[JobOffer]:
    cfg = get_matching_config()
    now = timezone.now()

    if widen:
        # Expire open offers from previous radius round.
        JobOffer.objects.filter(
            job=job, status__in=[JobOffer.Status.NOTIFIED, JobOffer.Status.SEEN]
        ).update(status=JobOffer.Status.EXPIRED, responded_at=now)
        new_radius = min(
            (job.match_radius_km or cfg.initial_radius_km) + cfg.widen_step_km,
            cfg.max_radius_km,
        )
        job.match_radius_km = new_radius
        job.match_round += 1
    else:
        if not job.match_radius_km:
            job.match_radius_km = cfg.initial_radius_km

    candidates = find_candidates(job, radius_km=job.match_radius_km)
    offers: list[JobOffer] = []
    expires = now + timedelta(seconds=cfg.offer_seconds)
    for profile, dist in candidates:
        offer = JobOffer.objects.create(
            job=job,
            worker=profile.user,
            distance_km=round(dist, 3),
            expires_at=expires,
            status=JobOffer.Status.NOTIFIED,
        )
        offers.append(offer)
        publish_event(
            event="offer:new",
            rooms=[f"user:{profile.user_id}"],
            payload={
                "job_id": str(job.id),
                "offer_id": str(offer.id),
                "expires_at": expires.isoformat(),
                "distance_km": offer.distance_km,
            },
        )

    prev = job.status
    if offers and job.status in {Job.Status.REQUESTED, Job.Status.OFFERED}:
        job.status = Job.Status.OFFERED
    job.last_match_at = now
    job.save(
        update_fields=[
            "status",
            "match_radius_km",
            "match_round",
            "last_match_at",
            "updated_at",
        ]
    )
    JobEvent.objects.create(
        job=job,
        event_type="offers_broadcast",
        from_status=prev,
        to_status=job.status,
        metadata={
            "count": len(offers),
            "radius_km": job.match_radius_km,
            "round": job.match_round,
            "widen": widen,
        },
    )
    return offers


def expire_due_offers(*, now=None) -> int:
    now = now or timezone.now()
    qs = JobOffer.objects.filter(
        status__in=[JobOffer.Status.NOTIFIED, JobOffer.Status.SEEN],
        expires_at__lte=now,
    )
    count = qs.update(status=JobOffer.Status.EXPIRED, responded_at=now)
    return count


def maybe_widen_job(job: Job, *, now=None) -> list[JobOffer]:
    """Expire due offers and widen radius when the interval elapsed."""
    now = now or timezone.now()
    cfg = get_matching_config()
    expire_due_offers(now=now)

    if job.status not in {Job.Status.REQUESTED, Job.Status.OFFERED}:
        return []
    if job.worker_id:
        return []
    if job.match_radius_km >= cfg.max_radius_km and not JobOffer.objects.filter(
        job=job, status__in=[JobOffer.Status.NOTIFIED, JobOffer.Status.SEEN]
    ).exists():
        # No more widening possible and nothing open — mark expired if never accepted.
        active = JobOffer.objects.filter(
            job=job, status__in=[JobOffer.Status.NOTIFIED, JobOffer.Status.SEEN]
        ).exists()
        if not active and job.status == Job.Status.OFFERED:
            # Allow another widen attempt only if under max; else expire job.
            if job.match_radius_km >= cfg.max_radius_km:
                job.status = Job.Status.EXPIRED
                job.save(update_fields=["status", "updated_at"])
                JobEvent.objects.create(
                    job=job, event_type="job_expired", to_status=Job.Status.EXPIRED
                )
                return []
        return []

    last = job.last_match_at or job.created_at
    if last and (now - last).total_seconds() < cfg.widen_interval_seconds:
        return []

    open_offers = JobOffer.objects.filter(
        job=job, status__in=[JobOffer.Status.NOTIFIED, JobOffer.Status.SEEN]
    ).exists()
    if open_offers:
        return []

    if job.match_radius_km >= cfg.max_radius_km:
        job.status = Job.Status.EXPIRED
        job.save(update_fields=["status", "updated_at"])
        return []

    return broadcast_offers(job, widen=True)
