from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User, WorkerProfile
from apps.catalog.models import ServiceCategory, WorkerService
from apps.jobs.cancellation import calculate_cancellation_fee
from apps.jobs.matching import broadcast_offers, maybe_widen_job
from apps.jobs.models import Job, JobOffer
from apps.scheduling.models import MatchingConfig
from apps.workers.models import Certificate


@pytest.fixture
def api():
    return APIClient()


def _user(email, phone, *, worker=False, customer=True, **extra):
    u = User.objects.create_user(
        email=email,
        password="password123",
        phone=phone,
        first_name=extra.pop("first_name", "Test"),
        last_name=extra.pop("last_name", "User"),
        role="WORKER" if worker else "CUSTOMER",
        active_profile="WORKER" if worker else "CUSTOMER",
        is_worker=worker,
        is_customer=customer,
        email_verified=True,
        phone_verified=True,
        **extra,
    )
    return u


def _category(slug="cleaning-home", certs=None, parent=None):
    return ServiceCategory.objects.create(
        slug=slug,
        name=slug,
        parent=parent,
        suggested_min_cents=15000,
        suggested_max_cents=40000,
        min_certificate_types=certs or [],
        commission_bps=1250,
        cancel_fee_bps=5000,
        cancel_window_minutes=120,
    )


def _worker(email, phone, lat, lng, category, *, certs=None, verified=True):
    u = _user(email, phone, worker=True)
    p = WorkerProfile.objects.create(
        user=u,
        display_name=u.get_full_name(),
        verification_status=(
            WorkerProfile.VerificationStatus.VERIFIED
            if verified
            else WorkerProfile.VerificationStatus.DRAFT
        ),
        bank_verified=verified,
        is_available=True,
        lat=lat,
        lng=lng,
        city="Cape Town",
        service_radius_km=25,
    )
    WorkerService.objects.create(worker=p, category=category, price_cents=20000)
    for c in certs or []:
        Certificate.objects.create(worker=p, cert_type=c, verified=True, number="T")
    return u, p


@pytest.mark.django_db
def test_instant_cleaning_accept_race(api):
    MatchingConfig.objects.get_or_create(name="default", defaults={"offer_seconds": 60})
    cat = _category()
    customer = _user("c@test.com", "+27821111111")
    w1, _ = _worker("w1@test.com", "+27821111112", -33.9249, 18.4241, cat)
    w2, _ = _worker("w2@test.com", "+27821111113", -33.9255, 18.4250, cat)

    api.force_authenticate(user=customer)
    res = api.post(
        "/api/v1/jobs/",
        {
            "category_id": str(cat.id),
            "title": "Flat clean",
            "description": "2-bed flat in CBD",
            "payment_method": "ESCROW",
            "budget_cents": 25000,
            "mode": "instant",
            "is_immediate": True,
            "address_line": "1 Long Street",
            "suburb": "Cape Town City Centre",
            "city": "Cape Town",
            "lat": -33.9249,
            "lng": 18.4241,
            "accept_cancellation_policy": True,
        },
        format="json",
    )
    assert res.status_code == 201, res.content
    job_id = res.data["id"]
    assert res.data["status"] in {"REQUESTED", "OFFERED"}
    assert JobOffer.objects.filter(job_id=job_id).count() >= 2

    o1 = JobOffer.objects.get(job_id=job_id, worker=w1)
    o2 = JobOffer.objects.get(job_id=job_id, worker=w2)

    api.force_authenticate(user=w1)
    a1 = api.post(f"/api/v1/jobs/{job_id}/offers/{o1.id}/accept/", {}, format="json")
    assert a1.status_code == 200, a1.content
    assert a1.data["status"] == "ACCEPTED"

    api.force_authenticate(user=w2)
    a2 = api.post(f"/api/v1/jobs/{job_id}/offers/{o2.id}/accept/", {}, format="json")
    assert a2.status_code == 409
    assert a2.data["code"] == "lost_race"
    o2.refresh_from_db()
    assert o2.status == "lost_race"


@pytest.mark.django_db
def test_offers_expire_and_radius_widens():
    cfg, _ = MatchingConfig.objects.get_or_create(name="default")
    cfg.offer_seconds = 1
    cfg.widen_interval_seconds = 0
    cfg.widen_step_km = 3
    cfg.initial_radius_km = 5
    cfg.max_radius_km = 20
    cfg.save()

    cat = _category()
    customer = _user("c2@test.com", "+27821111121")
    # Far worker ~8km — only after widen
    _worker("far@test.com", "+27821111122", -33.9800, 18.4800, cat)
    near, _ = _worker("near@test.com", "+27821111123", -33.9250, 18.4245, cat)

    job = Job.objects.create(
        customer=customer,
        category=cat,
        title="Clean",
        description="x",
        payment_method="CASH",
        budget_cents=20000,
        mode=Job.Mode.INSTANT,
        is_immediate=True,
        address_line="a",
        suburb="b",
        lat=-33.9249,
        lng=18.4241,
        match_radius_km=5,
        accept_cancellation_policy=True,
        status=Job.Status.REQUESTED,
    )
    offers = broadcast_offers(job)
    assert any(o.worker_id == near.id for o in offers)
    assert all(o.distance_km is None or o.distance_km <= 5.5 for o in offers)

    # Expire offers and force widen interval
    JobOffer.objects.filter(job=job).update(
        status=JobOffer.Status.EXPIRED, expires_at=timezone.now() - timedelta(seconds=1)
    )
    job.last_match_at = timezone.now() - timedelta(seconds=1)
    job.match_radius_km = 5
    job.save()
    new_offers = maybe_widen_job(job)
    job.refresh_from_db()
    assert job.match_radius_km >= 8
    assert len(new_offers) >= 1


@pytest.mark.django_db
def test_restricted_electrical_requires_certificate(api):
    MatchingConfig.objects.get_or_create(name="default")
    parent = _category("electrical")
    coc = _category(
        "electrical-coc",
        certs=["wireman_licence", "electrical_coc_authority"],
        parent=parent,
    )
    customer = _user("c3@test.com", "+27821111131")
    # Worker with skill but no cert
    bare, _ = _worker("bare@test.com", "+27821111132", -33.9249, 18.4241, coc)
    # Certified
    cert_user, _ = _worker(
        "cert@test.com",
        "+27821111133",
        -33.9250,
        18.4242,
        coc,
        certs=["wireman_licence", "electrical_coc_authority"],
    )

    api.force_authenticate(user=customer)
    res = api.post(
        "/api/v1/jobs/",
        {
            "category_id": str(coc.id),
            "title": "New installation CoC",
            "description": "Need CoC",
            "payment_method": "ESCROW",
            "budget_cents": 80000,
            "mode": "instant",
            "address_line": "2 Loop St",
            "suburb": "Cape Town",
            "lat": -33.9249,
            "lng": 18.4241,
            "accept_cancellation_policy": True,
        },
        format="json",
    )
    assert res.status_code == 201, res.content
    worker_ids = set(JobOffer.objects.filter(job_id=res.data["id"]).values_list("worker_id", flat=True))
    assert cert_user.id in worker_ids
    assert bare.id not in worker_ids


@pytest.mark.django_db
def test_scheduled_plumbing_quotes(api):
    MatchingConfig.objects.get_or_create(name="default")
    cat = _category("plumbing-leaks")
    customer = _user("c4@test.com", "+27821111141")
    w1, _ = _worker("p1@test.com", "+27821111142", -33.9249, 18.4241, cat)
    w2, _ = _worker("p2@test.com", "+27821111143", -33.9251, 18.4243, cat)

    api.force_authenticate(user=customer)
    start = timezone.now() + timedelta(days=2)
    res = api.post(
        "/api/v1/jobs/",
        {
            "category_id": str(cat.id),
            "title": "Fix leak",
            "description": "Kitchen tap",
            "payment_method": "CASH",
            "budget_cents": 35000,
            "mode": "scheduled",
            "is_immediate": False,
            "scheduled_at": start.isoformat(),
            "address_line": "10 Main Rd",
            "suburb": "Sea Point",
            "lat": -33.92,
            "lng": 18.39,
            "accept_cancellation_policy": True,
        },
        format="json",
    )
    assert res.status_code == 201, res.content
    job_id = res.data["id"]
    assert res.data["status"] == "REQUESTED"
    assert JobOffer.objects.filter(job_id=job_id).count() == 0

    api.force_authenticate(user=w1)
    q1 = api.post(
        f"/api/v1/jobs/{job_id}/quotes/",
        {"amount_cents": 32000, "message": "I can do Thursday"},
        format="json",
    )
    assert q1.status_code == 201, q1.content
    api.force_authenticate(user=w2)
    q2 = api.post(
        f"/api/v1/jobs/{job_id}/quotes/",
        {"amount_cents": 30000, "message": "Counter"},
        format="json",
    )
    assert q2.status_code == 201

    api.force_authenticate(user=customer)
    acc = api.post(f"/api/v1/jobs/{job_id}/quotes/{q2.data['id']}/accept/", {}, format="json")
    assert acc.status_code == 200, acc.content
    assert acc.data["status"] == "ACCEPTED"
    assert acc.data["agreed_price_cents"] == 30000
    assert acc.data["worker"]["id"] == str(w2.id)


@pytest.mark.django_db
def test_cancellation_math_roles_and_methods():
    cat = _category()
    customer = _user("c5@test.com", "+27821111151")
    worker, _ = _worker("w5@test.com", "+27821111152", -33.92, 18.42, cat)

    job = Job.objects.create(
        customer=customer,
        worker=worker,
        category=cat,
        title="x",
        description="y",
        payment_method=Job.PaymentMethod.ESCROW,
        budget_cents=10000,
        agreed_price_cents=10000,
        commission_bps=1250,
        cancel_fee_bps=5000,
        cancel_window_minutes=120,
        status=Job.Status.ACCEPTED,
        accepted_at=timezone.now(),
        address_line="a",
        suburb="b",
        mode=Job.Mode.INSTANT,
        accept_cancellation_policy=True,
    )
    snap = calculate_cancellation_fee(job, actor=customer)
    assert snap["is_late"] is True
    assert snap["fee_cents"] == 5000
    assert snap["customer_owes_cents"] == 5000
    assert snap["worker_receives_cents"] == 4375  # 5000 - 12.5%
    assert snap["platform_commission_cents"] == 625
    assert snap["escrow_refund_cents"] == 5000

    job.payment_method = Job.PaymentMethod.CASH
    snap_w = calculate_cancellation_fee(job, actor=worker)
    assert snap_w["cancelled_by"] == "worker"
    assert snap_w["customer_owes_cents"] == 0
    assert snap_w["worker_debt_cents"] == 5000

    # Free while still matching
    job.status = Job.Status.OFFERED
    job.worker = None
    free = calculate_cancellation_fee(job, actor=customer)
    assert free["is_late"] is False
    assert free["fee_cents"] == 0
