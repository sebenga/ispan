from __future__ import annotations

from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import ServiceCategory

from .cancellation import build_cancellation_policy_text, calculate_cancellation_fee
from .matching import maybe_widen_job
from .models import Job, JobOffer, Quote
from .realtime import latest_location, navigation_links
from .serializers import (
    JobCreateSerializer,
    JobOfferSerializer,
    JobSerializer,
    QuoteCreateSerializer,
    QuoteSerializer,
    RatingCreateSerializer,
    RatingSerializer,
)
from .services import (
    LostRaceError,
    accept_job_legacy,
    accept_offer,
    accept_quote,
    advance_status,
    cancel_job,
    create_job_pins,
    create_quote,
    decline_offer,
    rate_job,
    start_matching,
)


def _is_customer(user) -> bool:
    return bool(getattr(user, "is_customer", False) or user.role == "CUSTOMER")


def _is_worker(user) -> bool:
    return bool(getattr(user, "is_worker", False) or user.role == "WORKER")


def _is_staff(user) -> bool:
    return bool(user.is_staff or user.is_superuser or getattr(user, "is_support", False))


class JobListCreateView(APIView):
    def get(self, request):
        user = request.user
        qs = Job.objects.select_related("category", "customer", "worker").prefetch_related(
            "offers", "quotes"
        )
        if _is_staff(user):
            pass
        elif _is_worker(user) and request.query_params.get("scope") == "offers":
            qs = qs.filter(offers__worker=user).distinct()
        elif _is_worker(user) and not _is_customer(user):
            qs = qs.filter(Q(worker=user) | Q(offers__worker=user, offers__status__in=["notified", "seen"])).distinct()
        elif _is_customer(user) and not (_is_worker(user) and user.active_profile == "WORKER"):
            qs = qs.filter(customer=user)
        elif _is_worker(user) and user.active_profile == "WORKER":
            qs = qs.filter(Q(worker=user) | Q(offers__worker=user)).distinct()
        else:
            qs = qs.filter(customer=user)

        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return Response(JobSerializer(qs.order_by("-created_at")[:100], many=True).data)

    def post(self, request):
        if not _is_customer(request.user):
            return Response({"detail": "Customers only.", "code": "customers_only"}, status=403)
        ser = JobCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        try:
            category = ServiceCategory.objects.get(id=data["category_id"], is_active=True)
        except ServiceCategory.DoesNotExist:
            return Response({"detail": "Unknown category.", "code": "unknown_category"}, status=400)

        fee_bps = category.cancel_fee_bps
        window = category.cancel_window_minutes
        policy_text = build_cancellation_policy_text(fee_bps=fee_bps, window_minutes=window)
        mode = data["mode"]
        job = Job.objects.create(
            customer=request.user,
            category=category,
            title=data["title"],
            description=data["description"],
            payment_method=data["payment_method"],
            budget_cents=data.get("budget_cents"),
            agreed_price_cents=data.get("budget_cents"),
            commission_bps=category.commission_bps,
            cancel_fee_bps=fee_bps,
            cancel_window_minutes=window,
            cancellation_policy_text=policy_text,
            scheduled_at=data.get("scheduled_at"),
            is_immediate=mode == "instant",
            mode=mode,
            address_line=data["address_line"],
            suburb=data["suburb"],
            city=data.get("city", "Cape Town"),
            region=data.get("region", "Western Cape"),
            lat=data.get("lat"),
            lng=data.get("lng"),
            women_preferred=data.get("women_preferred", False),
            accept_cancellation_policy=True,
            match_radius_km=5,
            status=Job.Status.REQUESTED,
        )
        pins = create_job_pins(job)
        offers = []
        if mode == "instant":
            # Default CBD coords if client omitted GPS (Cape Town seed/tests).
            if job.lat is None or job.lng is None:
                job.lat = -33.9249
                job.lng = 18.4241
                job.save(update_fields=["lat", "lng", "updated_at"])
            offers = start_matching(job)

        job = Job.objects.select_related("category", "customer", "worker").prefetch_related(
            "offers", "quotes"
        ).get(id=job.id)
        payload = JobSerializer(job, context={"pins": pins}).data
        payload["offers_created"] = len(offers)
        return Response(payload, status=status.HTTP_201_CREATED)


class JobDetailView(APIView):
    def get(self, request, job_id):
        try:
            job = Job.objects.select_related("category", "customer", "worker").prefetch_related(
                "offers", "quotes"
            ).get(id=job_id)
        except Job.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)

        user = request.user
        allowed = (
            _is_staff(user)
            or job.customer_id == user.id
            or job.worker_id == user.id
            or job.offers.filter(worker=user).exists()
        )
        if not allowed:
            return Response({"detail": "Forbidden."}, status=403)

        # Tick matching widen for the customer polling the looking screen.
        if job.customer_id == user.id and job.status in {Job.Status.REQUESTED, Job.Status.OFFERED}:
            maybe_widen_job(job)
            job.refresh_from_db()

        ctx = {}
        if job.customer_id == user.id:
            # Do not re-send raw PINs after create; client should have stored them.
            # Include a flag that pins exist.
            ctx["pins"] = {"start_pin_set": bool(job.start_pin_hash), "finish_pin_set": bool(job.finish_pin_hash)}
        data = JobSerializer(job, context=ctx).data
        data["location"] = latest_location(job)
        data["navigation"] = navigation_links(job)
        return Response(data)


class JobCancelView(APIView):
    def post(self, request, job_id):
        try:
            job = Job.objects.select_related("category").get(id=job_id)
        except Job.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)
        if request.user.id not in {job.customer_id, job.worker_id} and not _is_staff(request.user):
            return Response({"detail": "Forbidden."}, status=403)
        preview = request.data.get("preview")
        if preview:
            return Response(calculate_cancellation_fee(job, actor=request.user))
        try:
            job = cancel_job(job=job, actor=request.user)
        except ValueError as exc:
            return Response({"detail": str(exc), "code": "cancel_failed"}, status=409)
        return Response(JobSerializer(job).data)


class JobAcceptView(APIView):
    def post(self, request, job_id):
        if not _is_worker(request.user):
            return Response({"detail": "Workers only."}, status=403)
        try:
            job = Job.objects.select_related("category").get(id=job_id)
        except Job.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)
        try:
            job = accept_job_legacy(job=job, worker=request.user)
        except LostRaceError:
            return Response({"detail": "Another worker accepted first.", "code": "lost_race"}, status=409)
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=403)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=409)
        return Response(JobSerializer(job).data)


class OfferAcceptView(APIView):
    def post(self, request, job_id, offer_id):
        try:
            offer = JobOffer.objects.select_related("job").get(id=offer_id, job_id=job_id)
        except JobOffer.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)
        try:
            job = accept_offer(offer=offer, worker=request.user)
        except LostRaceError:
            return Response({"detail": "Another worker accepted first.", "code": "lost_race"}, status=409)
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=403)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=409)
        return Response(JobSerializer(job).data)


class OfferDeclineView(APIView):
    def post(self, request, job_id, offer_id):
        try:
            offer = JobOffer.objects.select_related("job").get(id=offer_id, job_id=job_id)
        except JobOffer.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)
        try:
            offer = decline_offer(offer=offer, worker=request.user)
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=403)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=409)
        return Response(JobOfferSerializer(offer).data)


class MyOffersView(APIView):
    def get(self, request):
        if not _is_worker(request.user):
            return Response({"detail": "Workers only."}, status=403)
        # Expire / widen is customer-driven; still expire due offers for this worker.
        from .matching import expire_due_offers

        expire_due_offers()
        qs = (
            JobOffer.objects.filter(worker=request.user)
            .select_related("job", "job__category")
            .order_by("-notified_at")[:50]
        )
        rows = []
        for o in qs:
            rows.append(
                {
                    **JobOfferSerializer(o).data,
                    "job": {
                        "id": str(o.job_id),
                        "title": o.job.title,
                        "status": o.job.status,
                        "budget_cents": o.job.budget_cents,
                        "payment_method": o.job.payment_method,
                        "suburb": o.job.suburb,
                        "category": o.job.category.name,
                        "women_preferred": o.job.women_preferred,
                    },
                }
            )
        return Response({"results": rows})


class QuoteListCreateView(APIView):
    def get(self, request, job_id):
        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)
        if request.user.id not in {job.customer_id, job.worker_id} and not _is_worker(request.user):
            return Response({"detail": "Forbidden."}, status=403)
        return Response(QuoteSerializer(job.quotes.select_related("actor"), many=True).data)

    def post(self, request, job_id):
        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)
        if not _is_worker(request.user):
            return Response({"detail": "Workers only for counter-offers in MVP."}, status=403)
        ser = QuoteCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            quote = create_quote(
                job=job,
                actor=request.user,
                amount_cents=ser.validated_data["amount_cents"],
                message=ser.validated_data.get("message", ""),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)
        return Response(QuoteSerializer(quote).data, status=201)


class QuoteAcceptView(APIView):
    def post(self, request, job_id, quote_id):
        try:
            job = Job.objects.get(id=job_id)
            quote = Quote.objects.get(id=quote_id, job=job)
        except (Job.DoesNotExist, Quote.DoesNotExist):
            return Response({"detail": "Not found."}, status=404)
        try:
            job = accept_quote(job=job, quote=quote, customer=request.user)
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=403)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=409)
        return Response(JobSerializer(job).data)


class JobStatusView(APIView):
    def post(self, request, job_id):
        new_status = request.data.get("status")
        if not new_status:
            return Response({"detail": "status required"}, status=400)
        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)
        if request.user.id not in {job.customer_id, job.worker_id}:
            return Response({"detail": "Forbidden."}, status=403)
        try:
            job = advance_status(
                job=job, actor=request.user, new_status=new_status, pin=request.data.get("pin")
            )
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=403)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=409)
        return Response(JobSerializer(job).data)


class JobRateView(APIView):
    def post(self, request, job_id):
        ser = RatingCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)
        try:
            rating = rate_job(
                job=job,
                actor=request.user,
                score=ser.validated_data["score"],
                comment=ser.validated_data.get("comment", ""),
            )
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=403)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=409)
        return Response(RatingSerializer(rating).data)


class JobMatchTickView(APIView):
    """Customer/client can tick matching (expire + widen) while waiting."""

    def post(self, request, job_id):
        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)
        if job.customer_id != request.user.id and not _is_staff(request.user):
            return Response({"detail": "Forbidden."}, status=403)
        offers = maybe_widen_job(job)
        job.refresh_from_db()
        return Response(
            {
                "job": JobSerializer(job).data,
                "new_offers": len(offers),
                "server_time": timezone.now(),
            }
        )
