from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.db.models import Avg, Count
from django.utils import timezone

from apps.accounts.models import WorkerProfile
from apps.core.bus import publish_event

from .cancellation import calculate_cancellation_fee
from .matching import broadcast_offers
from .models import Job, JobEvent, JobOffer, Quote, Rating
from .pins import generate_pin, hash_pin, verify_pin

WORKER_TRANSITIONS = {
    Job.Status.ACCEPTED: {Job.Status.EN_ROUTE, Job.Status.CANCELLED},
    Job.Status.EN_ROUTE: {Job.Status.ARRIVED, Job.Status.CANCELLED},
    Job.Status.ARRIVED: {Job.Status.IN_PROGRESS, Job.Status.CANCELLED},
    Job.Status.IN_PROGRESS: {Job.Status.COMPLETED, Job.Status.CANCELLED},
}


class LostRaceError(Exception):
    code = "lost_race"


def job_rooms(job: Job) -> list[str]:
    rooms = [f"job:{job.id}", f"user:{job.customer_id}"]
    if job.worker_id:
        rooms.append(f"user:{job.worker_id}")
    return rooms


def emit_job(job: Job, event: str = "job:status") -> None:
    publish_event(
        event=event,
        rooms=job_rooms(job) + ["support"],
        payload={"job_id": str(job.id), "status": job.status},
    )


def log_event(job: Job, event_type: str, *, actor=None, from_status="", to_status="", **meta):
    JobEvent.objects.create(
        job=job,
        actor=actor,
        event_type=event_type,
        from_status=from_status,
        to_status=to_status or job.status,
        metadata=meta,
    )


def create_job_pins(job: Job) -> dict[str, str]:
    start = generate_pin()
    finish = generate_pin()
    job.start_pin_hash = hash_pin(start)
    job.finish_pin_hash = hash_pin(finish)
    job.save(update_fields=["start_pin_hash", "finish_pin_hash", "updated_at"])
    return {"start_pin": start, "finish_pin": finish}


@transaction.atomic
def accept_offer(*, offer: JobOffer, worker) -> Job:
    offer = JobOffer.objects.select_for_update().select_related("job").get(pk=offer.pk)
    job = Job.objects.select_for_update().get(pk=offer.job_id)

    if offer.worker_id != worker.id:
        raise PermissionError("Not your offer.")
    if offer.status not in {JobOffer.Status.NOTIFIED, JobOffer.Status.SEEN}:
        raise LostRaceError("Offer no longer available.")
    if offer.expires_at < timezone.now():
        offer.status = JobOffer.Status.EXPIRED
        offer.responded_at = timezone.now()
        offer.save(update_fields=["status", "responded_at", "updated_at"])
        raise ValueError("Offer expired.")
    if job.worker_id or job.status not in {Job.Status.REQUESTED, Job.Status.OFFERED, Job.Status.QUOTED}:
        offer.status = JobOffer.Status.LOST_RACE
        offer.responded_at = timezone.now()
        offer.save(update_fields=["status", "responded_at", "updated_at"])
        raise LostRaceError("lost_race")

    profile = getattr(worker, "worker_profile", None)
    if not profile or profile.verification_status != WorkerProfile.VerificationStatus.VERIFIED:
        raise ValueError("Worker must be verified to accept.")

    job.worker = worker
    job.status = Job.Status.ACCEPTED
    job.accepted_at = timezone.now()
    if job.agreed_price_cents is None:
        job.agreed_price_cents = job.budget_cents
    job.save()

    offer.status = JobOffer.Status.ACCEPTED
    offer.responded_at = timezone.now()
    offer.save(update_fields=["status", "responded_at", "updated_at"])

    JobOffer.objects.filter(
        job=job,
        status__in=[JobOffer.Status.NOTIFIED, JobOffer.Status.SEEN],
    ).exclude(pk=offer.pk).update(
        status=JobOffer.Status.LOST_RACE,
        responded_at=timezone.now(),
    )

    log_event(
        job,
        "offer_accepted",
        actor=worker,
        from_status=Job.Status.OFFERED,
        to_status=Job.Status.ACCEPTED,
        offer_id=str(offer.id),
    )
    emit_job(job, "job:accepted")
    return job


@transaction.atomic
def decline_offer(*, offer: JobOffer, worker) -> JobOffer:
    if offer.worker_id != worker.id:
        raise PermissionError("Not your offer.")
    if offer.status not in {JobOffer.Status.NOTIFIED, JobOffer.Status.SEEN}:
        raise ValueError("Offer not open.")
    offer.status = JobOffer.Status.DECLINED
    offer.responded_at = timezone.now()
    offer.save(update_fields=["status", "responded_at", "updated_at"])
    # Declining does not create a strike.
    log_event(offer.job, "offer_declined", actor=worker, offer_id=str(offer.id))
    return offer


@transaction.atomic
def accept_job_legacy(*, job: Job, worker) -> Job:
    """Compatibility: accept via job id by locating the worker's open offer, or creating one."""
    offer = (
        JobOffer.objects.filter(
            job=job,
            worker=worker,
            status__in=[JobOffer.Status.NOTIFIED, JobOffer.Status.SEEN],
        )
        .order_by("-notified_at")
        .first()
    )
    if not offer:
        # Direct accept race for OPEN board (tests / scheduled after quote).
        offer = JobOffer.objects.create(
            job=job,
            worker=worker,
            distance_km=None,
            expires_at=timezone.now() + timedelta(seconds=60),
            status=JobOffer.Status.NOTIFIED,
        )
    return accept_offer(offer=offer, worker=worker)


@transaction.atomic
def create_quote(*, job: Job, actor, amount_cents: int, message: str = "") -> Quote:
    if job.mode != Job.Mode.SCHEDULED and not job.scheduled_at:
        # Allow quotes on scheduled/quoted jobs primarily.
        if job.status not in {Job.Status.REQUESTED, Job.Status.QUOTED, Job.Status.OFFERED}:
            raise ValueError("Job not open for quotes.")
    if amount_cents < 1000:
        raise ValueError("Quote too low.")
    quote = Quote.objects.create(
        job=job, actor=actor, amount_cents=amount_cents, message=message or ""
    )
    if job.status in {Job.Status.REQUESTED, Job.Status.OFFERED}:
        prev = job.status
        job.status = Job.Status.QUOTED
        job.save(update_fields=["status", "updated_at"])
        log_event(job, "quote_proposed", actor=actor, from_status=prev, to_status=job.status)
    emit_job(job, "job:status")
    return quote


@transaction.atomic
def accept_quote(*, job: Job, quote: Quote, customer) -> Job:
    if customer.id != job.customer_id:
        raise PermissionError("Only the customer can accept a quote.")
    if quote.job_id != job.id:
        raise ValueError("Quote mismatch.")
    if quote.status != Quote.Status.PROPOSED:
        raise ValueError("Quote not open.")

    quote.status = Quote.Status.ACCEPTED
    quote.save(update_fields=["status", "updated_at"])
    Quote.objects.filter(job=job, status=Quote.Status.PROPOSED).exclude(pk=quote.pk).update(
        status=Quote.Status.REJECTED
    )

    worker = quote.actor
    if not getattr(worker, "is_worker", False):
        raise ValueError("Quote actor is not a worker.")

    job.worker = worker
    job.agreed_price_cents = quote.amount_cents
    job.status = Job.Status.ACCEPTED
    job.accepted_at = timezone.now()
    job.save()

    log_event(
        job,
        "quote_accepted",
        actor=customer,
        to_status=Job.Status.ACCEPTED,
        quote_id=str(quote.id),
        amount_cents=quote.amount_cents,
    )
    emit_job(job, "job:accepted")
    return job


@transaction.atomic
def advance_status(*, job: Job, actor, new_status: str, pin: str | None = None) -> Job:
    if new_status == Job.Status.CANCELLED:
        return cancel_job(job=job, actor=actor)

    if new_status == Job.Status.CONFIRMED:
        if actor.id != job.customer_id:
            raise PermissionError("Only customer can confirm completion")
        if job.status != Job.Status.COMPLETED:
            raise ValueError("Job not completed yet")
        job.status = Job.Status.CONFIRMED
        job.confirmed_at = timezone.now()
        job.save()
        log_event(job, "confirmed", actor=actor, to_status=job.status)
        emit_job(job, "job:status")
        return job

    if actor.id != job.worker_id:
        raise PermissionError("Only worker can update this status")
    allowed = WORKER_TRANSITIONS.get(job.status, set())
    if new_status not in allowed:
        raise ValueError(f"Cannot move from {job.status} to {new_status}")

    if new_status == Job.Status.IN_PROGRESS:
        if not verify_pin(pin or "", job.start_pin_hash):
            raise ValueError("Invalid start PIN.")
        job.started_at = timezone.now()
    if new_status == Job.Status.COMPLETED:
        if not verify_pin(pin or "", job.finish_pin_hash):
            raise ValueError("Invalid finish PIN.")
        job.completed_at = timezone.now()

    prev = job.status
    job.status = new_status
    job.save()
    log_event(job, "status", actor=actor, from_status=prev, to_status=new_status)
    emit_job(job)
    return job


@transaction.atomic
def cancel_job(*, job: Job, actor) -> Job:
    if job.status in {Job.Status.CANCELLED, Job.Status.CONFIRMED, Job.Status.EXPIRED}:
        raise ValueError("Job already closed.")

    snapshot = calculate_cancellation_fee(job, actor=actor)
    prev = job.status
    job.status = Job.Status.CANCELLED
    job.cancelled_at = timezone.now()
    job.cancelled_by = actor
    job.cancellation_fee_cents = snapshot["fee_cents"]
    job.cancellation_snapshot = snapshot
    job.save()

    # Soft-touch escrow refund math is recorded; capture/settlement is Phase 4.
    payment = getattr(job, "payment", None)
    if payment and snapshot.get("escrow_refund_cents") is not None:
        try:
            from apps.payments.escrow import refund_escrow
            from apps.payments.models import Payment

            if payment.method == Payment.Method.ESCROW and payment.status in {
                Payment.Status.HELD,
                Payment.Status.AUTHORIZED,
            }:
                refund_escrow(payment, snapshot["escrow_refund_cents"] or payment.amount_cents)
        except Exception:
            pass

    JobOffer.objects.filter(
        job=job, status__in=[JobOffer.Status.NOTIFIED, JobOffer.Status.SEEN]
    ).update(status=JobOffer.Status.EXPIRED, responded_at=timezone.now())

    log_event(
        job,
        "cancelled",
        actor=actor,
        from_status=prev,
        to_status=Job.Status.CANCELLED,
        **snapshot,
    )
    emit_job(job, "job:status")
    return job


@transaction.atomic
def rate_job(*, job: Job, actor, score: int, comment: str = "") -> Rating:
    if job.status not in {Job.Status.COMPLETED, Job.Status.CONFIRMED}:
        raise ValueError("Job not completed")
    is_customer = actor.id == job.customer_id
    is_worker = actor.id == job.worker_id
    if not is_customer and not is_worker:
        raise PermissionError("Forbidden")
    to_user = job.worker if is_customer else job.customer
    if not to_user:
        raise ValueError("No counterpart")

    rating, _ = Rating.objects.update_or_create(
        job=job,
        from_user=actor,
        defaults={"to_user": to_user, "score": score, "comment": comment},
    )

    if is_customer and job.worker_id:
        agg = Rating.objects.filter(to_user_id=job.worker_id).aggregate(
            avg=Avg("score"), count=Count("id")
        )
        WorkerProfile.objects.filter(user_id=job.worker_id).update(
            avg_rating=agg["avg"] or 0,
            rating_count=agg["count"] or 0,
        )
    return rating


def start_matching(job: Job) -> list[JobOffer]:
    if job.mode == Job.Mode.SCHEDULED:
        # Scheduled jobs wait for quotes; optional soft broadcast for awareness.
        return []
    return broadcast_offers(job, widen=False)
