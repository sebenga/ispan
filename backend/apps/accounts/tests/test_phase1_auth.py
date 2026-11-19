import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.accounts.models import User, WorkerProfile
from apps.common.sa_id import is_valid_sa_id
from apps.legal.models import LegalConsent


@pytest.fixture
def api():
    return APIClient()


def _valid_sa_id() -> str:
    for n in range(100_000):
        candidate = f"900101{n:07d}"
        if is_valid_sa_id(candidate):
            return candidate
    raise RuntimeError("could not build SA ID")


@pytest.mark.django_db
def test_sa_id_checksum():
    assert is_valid_sa_id(_valid_sa_id()) is True
    assert is_valid_sa_id("123") is False
    assert is_valid_sa_id("abcdefghijklm") is False
    assert is_valid_sa_id("900101580008X") is False


@pytest.mark.django_db
def test_register_login_jwt_and_otp(api):
    res = api.post(
        "/api/v1/auth/register/",
        {
            "email": "newworker@ispan.test",
            "phone": "+27821110001",
            "password": "password123",
            "first_name": "Anele",
            "last_name": "Dlamini",
            "role": "WORKER",
            "consent_version": "2026-11-19",
            "consent_flags": {"age_18": True, "terms": True, "privacy": True},
        },
        format="json",
    )
    assert res.status_code == 201, res.content
    assert "access" in res.data
    assert res.data["user"]["is_worker"] is True
    assert LegalConsent.objects.filter(user_id=res.data["user"]["id"]).exists()

    api.credentials(HTTP_AUTHORIZATION=f"Bearer {res.data['access']}")
    otp = api.post(
        "/api/v1/auth/otp/verify/",
        {"purpose": "signup_email", "destination": "newworker@ispan.test", "code": "123456"},
        format="json",
    )
    assert otp.status_code == 200, otp.content
    otp2 = api.post(
        "/api/v1/auth/otp/verify/",
        {"purpose": "signup_phone", "destination": "+27821110001", "code": "123456"},
        format="json",
    )
    assert otp2.status_code == 200

    me = api.get("/api/v1/auth/me/")
    assert me.data["email_verified"] is True
    assert me.data["phone_verified"] is True

    login = api.post(
        "/api/v1/auth/login/",
        {"email": "newworker@ispan.test", "password": "password123"},
        format="json",
    )
    assert login.status_code == 200
    assert "access" in login.data


@pytest.mark.django_db
def test_consent_version_stored(api):
    res = api.post(
        "/api/legal/consent/",
        {
            "version": "2026-11-19",
            "flags": {"age_18": True, "terms": True, "privacy": True},
            "anon_id": "anon-1",
        },
        format="json",
    )
    assert res.status_code == 201, res.content
    assert LegalConsent.objects.filter(version="2026-11-19", anon_id="anon-1").exists()


@pytest.mark.django_db
def test_verification_state_machine(api, tmp_path, settings):
    settings.PRIVATE_MEDIA_ROOT = str(tmp_path)
    settings.MEDIA_ENCRYPTION_KEY = "test-encryption-key-for-phase1"
    settings.DEBUG = True

    sa_id = _valid_sa_id()

    reg = api.post(
        "/api/v1/auth/register/",
        {
            "email": "verify@ispan.test",
            "phone": "+27821110002",
            "password": "password123",
            "first_name": "Lebo",
            "last_name": "Mokoena",
            "role": "WORKER",
        },
        format="json",
    )
    assert reg.status_code == 201, reg.content
    token = reg.data["access"]
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    assert (
        api.post(
            "/api/v1/auth/otp/verify/",
            {"purpose": "signup_email", "destination": "verify@ispan.test", "code": "123456"},
            format="json",
        ).status_code
        == 200
    )
    assert (
        api.post(
            "/api/v1/auth/otp/verify/",
            {"purpose": "signup_phone", "destination": "+27821110002", "code": "123456"},
            format="json",
        ).status_code
        == 200
    )

    pdf = SimpleUploadedFile("id.pdf", b"%PDF-1.4 fake", content_type="application/pdf")
    doc = api.post(
        "/api/v1/workers/me/documents/",
        {"doc_type": "sa_id", "id_number": sa_id, "file": pdf},
        format="multipart",
    )
    assert doc.status_code == 201, doc.content

    bank = api.put(
        "/api/v1/workers/me/bank/",
        {
            "holder_name": "Lebo Mokoena",
            "bank_name": "Capitec",
            "account_number": "1234567890",
            "branch_code": "470010",
        },
        format="json",
    )
    assert bank.status_code == 200, bank.content

    submit = api.post("/api/v1/workers/me/submit/", {}, format="json")
    assert submit.status_code == 200, submit.content
    assert submit.data["verification_status"] == "SUBMITTED"

    profile = WorkerProfile.objects.get(user__email="verify@ispan.test")
    assert profile.can_receive_payouts is False

    admin = User.objects.create_superuser(
        email="admin@ispan.test",
        password="password123",
        phone="+27829990000",
        first_name="Admin",
        last_name="User",
        role="ADMIN",
        is_support=True,
    )
    api.force_authenticate(user=admin)
    approve = api.post(
        f"/api/v1/admin/verification/{profile.id}/",
        {"decision": "approve"},
        format="json",
    )
    assert approve.status_code == 200, approve.content
    profile.refresh_from_db()
    assert profile.verification_status == "VERIFIED"
    assert profile.can_receive_payouts is True
