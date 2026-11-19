from __future__ import annotations

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import ServiceCategory
from apps.payments.escrow import authorize_escrow, create_payment_for_job, hold_escrow

from .models import Job
from .serializers import (
    JobCreateSerializer,
    JobSerializer,
    RatingCreateSerializer,
    RatingSerializer,
)
from .services import accept_job, advance_status, rate_job

User = get_user_model()


class JobListCreateView(APIView):
    def get(self, request):
        user = request.user
        qs = Job.objects.select_related("category", "customer", "worker", "payment")
        if user.role == User.Role.CUSTOMER:
            qs = qs.filter(customer=user)
        elif user.role == User.Role.WORKER:
            qs = qs.filter(worker=user) | qs.filter(status=Job.Status.OPEN, worker__isnull=True)
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return Response(JobSerializer(qs.distinct().order_by("-created_at"), many=True).data)

    def post(self, request):
        if request.user.role != User.Role.CUSTOMER:
            return Response({"detail": "Customers only."}, status=403)
        ser = JobCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        try:
            category = ServiceCategory.objects.get(id=data["category_id"])
        except ServiceCategory.DoesNotExist:
            return Response({"detail": "Unknown category."}, status=400)

        commission_bps = settings.COMMISSION_BPS
        job = Job.objects.create(
            customer=request.user,
            category=category,
            title=data["title"],
            description=data["description"],
            payment_method=data["payment_method"],
            budget_cents=data["budget_cents"],
            agreed_price_cents=data["budget_cents"],
            commission_bps=commission_bps,
            scheduled_at=data.get("scheduled_at"),
            is_immediate=data.get("is_immediate", True),
            address_line=data["address_line"],
            suburb=data["suburb"],
            city=data.get("city", "Cape Town"),
            lat=data.get("lat"),
            lng=data.get("lng"),
        )
        payment = create_payment_for_job(
            job=job,
            method=data["payment_method"],
            amount_cents=data["budget_cents"],
            commission_bps=commission_bps,
        )
        if data["payment_method"] == Job.PaymentMethod.ESCROW:
            authorize_escrow(payment, request.user.email)
            hold_escrow(payment)

        job = Job.objects.select_related("category", "payment").get(id=job.id)
        return Response(JobSerializer(job).data, status=status.HTTP_201_CREATED)


class JobDetailView(APIView):
    def get(self, request, job_id):
        try:
            job = Job.objects.select_related(
                "category", "customer", "worker", "payment"
            ).prefetch_related("payment__ledger").get(id=job_id)
        except Job.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)

        user = request.user
        if (
            user.role != User.Role.ADMIN
            and job.customer_id != user.id
            and job.worker_id != user.id
            and job.status != Job.Status.OPEN
        ):
            return Response({"detail": "Forbidden."}, status=403)
        return Response(JobSerializer(job).data)


class JobAcceptView(APIView):
    def post(self, request, job_id):
        if request.user.role != User.Role.WORKER:
            return Response({"detail": "Workers only."}, status=403)
        try:
            job = Job.objects.select_related("payment", "category").get(id=job_id)
        except Job.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)
        try:
            job = accept_job(job=job, worker=request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=409)
        return Response(JobSerializer(job).data)


class JobStatusView(APIView):
    def post(self, request, job_id):
        new_status = request.data.get("status")
        if not new_status:
            return Response({"detail": "status required"}, status=400)
        try:
            job = Job.objects.select_related("payment").get(id=job_id)
        except Job.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)
        if request.user.id not in {job.customer_id, job.worker_id}:
            return Response({"detail": "Forbidden."}, status=403)
        try:
            job = advance_status(job=job, actor=request.user, new_status=new_status)
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
