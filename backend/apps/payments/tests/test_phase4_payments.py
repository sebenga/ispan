from datetime import timedelta

import pytest
from django.conf import settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User, WorkerProfile
from apps.catalog.models import ServiceCategory, WorkerService
from apps.jobs.models import Job
from apps.jobs.pins import hash_pin
from apps.payments.models import Payment, Receipt, Wallet, WebhookEvent
from apps.payments.services import run_auto_releases
from apps.workers.models import BankAccount


@pytest.fixture
def api():
    return APIClient()


def _users_and_job(*, method="ESCROW", amount=10000):
    cat = ServiceCategory.objects.create(
        slug=f"pay-{method.lower()}",
        name="Pay Cat",
        suggested_min_cents=10000,
        suggested_max_cents=50000,
        commission_bps=1250,
    )
    customer = User.objects.create_user(
        email=f"cust-{method.lower()}@test.com",
        password="password123",
        phone=f"+2782112{method[:4]}1",
        first_name="Cust",
        last_name="Test",
        role="CUSTOMER",
        is_customer=True,
        email_verified=True,
        phone_verified=True,
    )
    worker = User.objects.create_user(
        email=f"work-{method.lower()}@test.com",
        password="password123",
        phone=f"+2782112{method[:4]}2",
        first_name="Work",
        last_name="Test",
        role="WORKER",
        is_worker=True,
        is_customer=True,
        email_verified=True,
        phone_verified=True,
    )
    profile = WorkerProfile.objects.create(
        user=worker,
        verification_status=WorkerProfile.VerificationStatus.VERIFIED,
        bank_verified=True,
        is_available=True,
        lat=-33.92,
        lng=18.42,
        city="Cape Town",
        bank_account_masked="****1234",
    )
    BankAccount.objects.create(
        worker=profile,
        holder_name="Work Test",
        bank_name="Capitec",
        account_number_encrypted="x",
        account_number_masked="****1234",
        verification_status=BankAccount.VerificationStatus.VERIFIED,
    )
    WorkerService.objects.create(worker=profile, category=cat, price_cents=amount)
    job = Job.objects.create(
        customer=customer,
        worker=worker,
        category=cat,
        title="Paid job",
        description="x",
        payment_method=method,
        budget_cents=amount,
        agreed_price_cents=amount,
        commission_bps=1250,
        status=Job.Status.ACCEPTED,
        mode=Job.Mode.INSTANT,
        address_line="1 St",
        suburb="CBD",
        lat=-33.92,
        lng=18.42,
        accept_cancellation_policy=True,
        start_pin_hash=hash_pin("1111"),
        finish_pin_hash=hash_pin("2222"),
    )
    return customer, worker, job, profile


def _complete_and_confirm(api, job, customer, worker):
    api.force_authenticate(user=worker)
    assert api.post(
        f"/api/v1/jobs/{job.id}/status/",
        {"status": "EN_ROUTE"},
        format="json",
    ).status_code == 200
    assert api.post(
        f"/api/v1/jobs/{job.id}/status/",
        {"status": "ARRIVED"},
        format="json",
    ).status_code == 200
    assert api.post(
        f"/api/v1/jobs/{job.id}/status/",
        {"status": "IN_PROGRESS", "pin": "1111"},
        format="json",
    ).status_code == 200
    assert api.post(
        f"/api/v1/jobs/{job.id}/status/",
        {"status": "COMPLETED", "pin": "2222"},
        format="json",
    ).status_code == 200
    api.force_authenticate(user=customer)
    res = api.post(f"/api/v1/jobs/{job.id}/status/", {"status": "CONFIRMED"}, format="json")
    return res


@pytest.mark.django_db
def test_escrow_happy_path(api):
    customer, worker, job, _ = _users_and_job(method="ESCROW", amount=10000)
    api.force_authenticate(user=customer)
    pay = api.post(
        f"/api/v1/jobs/{job.id}/pay/escrow/",
        {"test_card": "succeed"},
        format="json",
    )
    assert pay.status_code == 200, pay.content
    assert pay.data["payment"]["status"] == "HELD"

    conf = _complete_and_confirm(api, job, customer, worker)
    assert conf.status_code == 200, conf.content
    wallet = Wallet.objects.get(worker=worker)
    assert wallet.available_cents == 8750  # 10000 - 12.5%
    assert wallet.pending_cents == 0
    assert Receipt.objects.filter(job=job).count() >= 1
    receipt = api.get(f"/api/v1/jobs/{job.id}/receipt/")
    assert receipt.status_code == 200


@pytest.mark.django_db
def test_failed_test_card(api):
    customer, worker, job, _ = _users_and_job(method="ESCROW", amount=10000)
    # unique emails - use different slug path by recreating with fail suffix via phone uniqueness
    api.force_authenticate(user=customer)
    pay = api.post(
        f"/api/v1/jobs/{job.id}/pay/escrow/",
        {"test_card": "fail"},
        format="json",
    )
    assert pay.status_code == 402
    assert Payment.objects.filter(job=job, status="FAILED").exists()
    job.refresh_from_db()
    assert job.status == "ACCEPTED"  # job itself is unchanged


@pytest.mark.django_db
def test_webhook_idempotency(api):
    customer, worker, job, _ = _users_and_job(method="ESCROW", amount=20000)
    api.force_authenticate(user=customer)
    pay = api.post(
        f"/api/v1/jobs/{job.id}/pay/escrow/",
        {"test_card": "webhook_delay"},
        format="json",
    )
    assert pay.status_code == 200
    payment = Payment.objects.get(job=job)
    assert payment.status == "AUTHORIZED"
    ref = payment.provider_ref
    payload = {"event_id": "evt-1", "reference": ref, "status": "success"}
    wh1 = api.post("/api/v1/payments/webhooks/mock/", payload, format="json")
    assert wh1.status_code == 200
    assert wh1.data["result"] == "held"
    payment.refresh_from_db()
    assert payment.status == "HELD"
    wh2 = api.post("/api/v1/payments/webhooks/mock/", payload, format="json")
    assert wh2.data["duplicate"] is True
    assert WebhookEvent.objects.filter(event_id="evt-1").count() == 1


@pytest.mark.django_db
def test_auto_release(api, settings):
    settings.ESCROW_AUTO_RELEASE_HOURS = 0
    customer, worker, job, _ = _users_and_job(method="ESCROW", amount=10000)
    # Need unique users - the helper uses method in email; create second job carefully
    api.force_authenticate(user=customer)
    api.post(f"/api/v1/jobs/{job.id}/pay/escrow/", {"test_card": "succeed"}, format="json")
    job.status = Job.Status.COMPLETED
    job.completed_at = timezone.now()
    job.save()
    payment = Payment.objects.get(job=job)
    payment.auto_release_at = timezone.now() - timedelta(seconds=1)
    payment.save()
    n = run_auto_releases()
    assert n == 1
    payment.refresh_from_db()
    assert payment.status == "RELEASED"
    wallet = Wallet.objects.get(worker=worker)
    assert wallet.available_cents == 8750


@pytest.mark.django_db
def test_cash_debt_blocks_accept(api):
    customer, worker, job, profile = _users_and_job(method="CASH", amount=20000)
    conf = _complete_and_confirm(api, job, customer, worker)
    assert conf.status_code == 200, conf.content
    wallet = Wallet.objects.get(worker=worker)
    assert wallet.debt_cents == 2500  # 12.5% of 20000

    # Push debt over threshold
    wallet.debt_cents = settings.CASH_DEBT_BLOCK_CENTS
    wallet.save()

    cat = job.category
    customer2 = User.objects.create_user(
        email="cust2-cash@test.com",
        password="password123",
        phone="+27821129991",
        first_name="C2",
        last_name="T",
        role="CUSTOMER",
        is_customer=True,
    )
    job2 = Job.objects.create(
        customer=customer2,
        category=cat,
        title="Another",
        description="y",
        payment_method="CASH",
        budget_cents=15000,
        status=Job.Status.OFFERED,
        mode=Job.Mode.INSTANT,
        address_line="2 St",
        suburb="CBD",
        lat=-33.92,
        lng=18.42,
        accept_cancellation_policy=True,
    )
    from apps.jobs.models import JobOffer

    offer = JobOffer.objects.create(
        job=job2,
        worker=worker,
        expires_at=timezone.now() + timedelta(minutes=5),
        status="notified",
    )
    api.force_authenticate(user=worker)
    res = api.post(f"/api/v1/jobs/{job2.id}/offers/{offer.id}/accept/", {}, format="json")
    assert res.status_code == 409
    assert "debt" in res.data["detail"].lower()


@pytest.mark.django_db
def test_payout_fica_gate(api):
    customer, worker, job, profile = _users_and_job(method="ESCROW", amount=50000)
    api.force_authenticate(user=customer)
    api.post(f"/api/v1/jobs/{job.id}/pay/escrow/", {"test_card": "succeed"}, format="json")
    conf = _complete_and_confirm(api, job, customer, worker)
    assert conf.status_code == 200

    # Unverified blocked
    profile.verification_status = WorkerProfile.VerificationStatus.DRAFT
    profile.save()
    api.force_authenticate(user=worker)
    blocked = api.post("/api/v1/wallets/me/payouts/", {}, format="json")
    assert blocked.status_code == 403
    assert blocked.data["code"] == "fica_blocked"

    profile.verification_status = WorkerProfile.VerificationStatus.VERIFIED
    profile.bank_verified = True
    profile.save()
    ok = api.post("/api/v1/wallets/me/payouts/", {}, format="json")
    assert ok.status_code == 201, ok.content
    assert ok.data["status"] == "PAID"
    wallet = Wallet.objects.get(worker=worker)
    assert wallet.available_cents == 0
