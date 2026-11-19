from __future__ import annotations

from django.db import transaction
from django.db.models import Avg, Count
from django.utils import timezone

from apps.accounts.models import WorkerProfile
from apps.core.bus import publish_event
from apps.payments.escrow import confirm_cash, refund_escrow, release_escrow
from apps.payments.models import Payment

from .models import Job, Rating

WORKER_TRANSITIONS = {
    Job.Status.ACCEPTED: {Job.Status.EN_ROUTE, Job.Status.CANCELLED},
    Job.Status.EN_ROUTE: {Job.Status.IN_PROGRESS, Job.Status.CANCELLED},
    Job.Status.IN_PROGRESS: {Job.Status.AWAITING_CONFIRMATION, Job.Status.CANCELLED},
}


def job_rooms(job: Job) -> list[str]:
    rooms = [f"job:{job.id}", f"user:{job.customer_id}"]
    if job.worker_id:
        rooms.append(f"user:{job.worker_id}")
    return rooms


def emit_job(job: Job, event: str = "job.updated") -> None:
    publish_event(
        event=event,
        rooms=job_rooms(job),
        payload={"job_id": str(job.id), "status": job.status},
    )


@transaction.atomic
def accept_job(*, job: Job, worker) -> Job:
    if job.status != Job.Status.OPEN or job.worker_id:
        raise ValueError("Job not available")
    profile = getattr(worker, "worker_profile", None)
    if not profile or profile.verification_status == WorkerProfile.VerificationStatus.REJECTED:
        raise ValueError("Worker profile not eligible")
    job.worker = worker
    job.status = Job.Status.ACCEPTED
    job.agreed_price_cents = job.budget_cents
    job.save()
    emit_job(job, "job.accepted")
    return job


@transaction.atomic
def advance_status(*, job: Job, actor, new_status: str) -> Job:
    if new_status == Job.Status.CANCELLED:
        return cancel_job(job=job, actor=actor)

    if new_status == Job.Status.COMPLETED:
        if actor.id != job.customer_id:
            raise PermissionError("Only customer can confirm completion")
        if job.status != Job.Status.AWAITING_CONFIRMATION:
            raise ValueError("Job not awaiting confirmation")
        return complete_job(job)

    if actor.id != job.worker_id:
        raise PermissionError("Only worker can update this status")
    allowed = WORKER_TRANSITIONS.get(job.status, set())
    if new_status not in allowed:
        raise ValueError(f"Cannot move from {job.status} to {new_status}")

    job.status = new_status
    if new_status == Job.Status.IN_PROGRESS:
        job.started_at = timezone.now()
    job.save()
    emit_job(job)
    return job


@transaction.atomic
def complete_job(job: Job) -> Job:
    payment = getattr(job, "payment", None)
    if payment:
        if payment.method == Payment.Method.ESCROW:
            release_escrow(payment)
        elif payment.method == Payment.Method.CASH:
            confirm_cash(payment)

    job.status = Job.Status.COMPLETED
    job.completed_at = timezone.now()
    job.save()

    if job.worker_id:
        from django.db.models import F

        WorkerProfile.objects.filter(user_id=job.worker_id).update(
            completed_jobs=F("completed_jobs") + 1
        )

    emit_job(job, "job.completed")
    return job


@transaction.atomic
def cancel_job(*, job: Job, actor) -> Job:
    late = job.status in {
        Job.Status.ACCEPTED,
        Job.Status.EN_ROUTE,
        Job.Status.IN_PROGRESS,
        Job.Status.AWAITING_CONFIRMATION,
    }
    payment = getattr(job, "payment", None)
    if (
        payment
        and payment.method == Payment.Method.ESCROW
        and payment.status in {Payment.Status.HELD, Payment.Status.AUTHORIZED}
    ):
        if late:
            fee = round(payment.amount_cents * job.cancel_fee_bps / 10000)
            refund = max(payment.amount_cents - fee, 0)
            refund_escrow(payment, refund or payment.amount_cents)
        else:
            refund_escrow(payment)

    job.status = Job.Status.CANCELLED
    job.cancelled_at = timezone.now()
    job.cancelled_by = actor
    job.save()
    emit_job(job, "job.cancelled")
    return job


@transaction.atomic
def rate_job(*, job: Job, actor, score: int, comment: str = "") -> Rating:
    if job.status != Job.Status.COMPLETED:
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
