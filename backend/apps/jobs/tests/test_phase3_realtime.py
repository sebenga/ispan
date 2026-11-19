import pytest
from django.conf import settings
from rest_framework.test import APIClient

from apps.accounts.models import User, WorkerProfile
from apps.catalog.models import ServiceCategory, WorkerService
from apps.jobs.models import Job, Message
from apps.safety.models import EmergencyContact, SosEvent
from apps.scheduling.models import MatchingConfig


@pytest.fixture
def api():
    return APIClient()


def _user(email, phone, *, worker=False, support=False):
    return User.objects.create_user(
        email=email,
        password="password123",
        phone=phone,
        first_name="Test",
        last_name="User",
        role="WORKER" if worker else "CUSTOMER",
        active_profile="WORKER" if worker else "CUSTOMER",
        is_worker=worker,
        is_customer=not worker,
        is_support=support,
        is_staff=support,
        email_verified=True,
        phone_verified=True,
    )


def _job_pair():
    MatchingConfig.objects.get_or_create(name="default")
    cat = ServiceCategory.objects.create(
        slug="cleaning-rt",
        name="Cleaning RT",
        suggested_min_cents=15000,
        suggested_max_cents=40000,
    )
    customer = _user("cust-rt@test.com", "+27821118001")
    worker = _user("work-rt@test.com", "+27821118002", worker=True)
    profile = WorkerProfile.objects.create(
        user=worker,
        verification_status=WorkerProfile.VerificationStatus.VERIFIED,
        bank_verified=True,
        is_available=True,
        lat=-33.9249,
        lng=18.4241,
        city="Cape Town",
    )
    WorkerService.objects.create(worker=profile, category=cat, price_cents=20000)
    EmergencyContact.objects.create(
        user=customer, name="Sister", phone="+27821118999", is_primary=True
    )
    job = Job.objects.create(
        customer=customer,
        worker=worker,
        category=cat,
        title="Live job",
        description="Tracking test",
        payment_method=Job.PaymentMethod.CASH,
        budget_cents=20000,
        agreed_price_cents=20000,
        status=Job.Status.ACCEPTED,
        mode=Job.Mode.INSTANT,
        address_line="1 Long St",
        suburb="CBD",
        lat=-33.9249,
        lng=18.4241,
        accept_cancellation_policy=True,
    )
    return customer, worker, job


@pytest.mark.django_db
def test_location_rejected_outside_active_statuses(api):
    customer, worker, job = _job_pair()
    api.force_authenticate(user=worker)
    # ACCEPTED is not a location-allowed status
    res = api.post(
        f"/api/v1/jobs/{job.id}/location/",
        {"lat": -33.92, "lng": 18.42},
        format="json",
    )
    assert res.status_code == 409
    assert res.data["code"] == "location_not_allowed"

    job.status = Job.Status.EN_ROUTE
    job.save(update_fields=["status"])
    ok = api.post(
        f"/api/v1/jobs/{job.id}/location/",
        {"lat": -33.921, "lng": 18.421, "accuracy_m": 12},
        format="json",
    )
    assert ok.status_code == 201, ok.content
    assert ok.data["eta_minutes"] is not None

    # Customer can recover last ping via REST
    api.force_authenticate(user=customer)
    latest = api.get(f"/api/v1/jobs/{job.id}/location/")
    assert latest.status_code == 200
    assert latest.data["latest"]["lat"] == -33.921
    assert latest.data["navigation"]["google_maps"]
    assert "waze.com" in latest.data["navigation"]["waze"]


@pytest.mark.django_db
def test_chat_persists_and_reloads(api):
    customer, worker, job = _job_pair()
    api.force_authenticate(user=customer)
    sent = api.post(
        f"/api/v1/jobs/{job.id}/chat/",
        {"body": "Please use the side gate"},
        format="json",
    )
    assert sent.status_code == 201, sent.content
    assert Message.objects.filter(job=job).count() == 1

    api.force_authenticate(user=worker)
    hist = api.get(f"/api/v1/jobs/{job.id}/chat/")
    assert hist.status_code == 200
    assert hist.data["results"][0]["body"] == "Please use the side gate"


@pytest.mark.django_db
def test_sos_creates_event_and_mock_sms(api):
    customer, worker, job = _job_pair()
    api.force_authenticate(user=customer)
    res = api.post(
        f"/api/v1/jobs/{job.id}/sos/",
        {"lat": -33.92, "lng": 18.42, "note": "Felt unsafe"},
        format="json",
    )
    assert res.status_code == 201, res.content
    assert "10111" in res.data["disclaimer"]
    assert SosEvent.objects.filter(job=job).count() == 1
    event = SosEvent.objects.get(job=job)
    assert event.support_notified is True
    assert len(event.notified_parties) >= 1


@pytest.mark.django_db
def test_realtime_room_authorization(api):
    customer, worker, job = _job_pair()
    stranger = _user("stranger@test.com", "+27821118003")
    headers = {"HTTP_X_INTERNAL_TOKEN": settings.INTERNAL_API_TOKEN}

    allow = api.post(
        "/api/v1/internal/realtime/authorize/",
        {"user_id": str(customer.id), "room": f"job:{job.id}"},
        format="json",
        **headers,
    )
    assert allow.status_code == 200
    assert allow.data["allowed"] is True

    deny = api.post(
        "/api/v1/internal/realtime/authorize/",
        {"user_id": str(stranger.id), "room": f"job:{job.id}"},
        format="json",
        **headers,
    )
    assert deny.status_code == 200
    assert deny.data["allowed"] is False

    support = _user("support@test.com", "+27821118004", support=True)
    support_room = api.post(
        "/api/v1/internal/realtime/authorize/",
        {"user_id": str(support.id), "room": "support"},
        format="json",
        **headers,
    )
    assert support_room.data["allowed"] is True

    no_token = api.post(
        "/api/v1/internal/realtime/authorize/",
        {"user_id": str(customer.id), "room": f"job:{job.id}"},
        format="json",
    )
    assert no_token.status_code == 401
