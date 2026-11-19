from __future__ import annotations

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.core.models import BaseModel, UUIDModel


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra):
        if not email:
            raise ValueError("Users must have an email address.")
        user = self.model(email=self.normalize_email(email), **extra)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email: str, password: str, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("is_active", True)
        extra.setdefault("is_support", True)
        return self._create_user(email, password, **extra)


class User(UUIDModel, AbstractBaseUser, PermissionsMixin):
    class ActiveProfile(models.TextChoices):
        CUSTOMER = "CUSTOMER", "Customer"
        WORKER = "WORKER", "Worker"

    email = models.EmailField(unique=True, db_index=True)
    phone = models.CharField(max_length=20, unique=True)
    # Legacy single-role field kept for compatibility; dual profiles use flags below.
    role = models.CharField(max_length=20, default=ActiveProfile.CUSTOMER)
    is_customer = models.BooleanField(default=False)
    is_worker = models.BooleanField(default=False)
    is_support = models.BooleanField(default=False)
    active_profile = models.CharField(
        max_length=20, choices=ActiveProfile.choices, default=ActiveProfile.CUSTOMER
    )
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    preferred_language = models.CharField(max_length=8, default="en")
    avatar_url = models.URLField(blank=True)
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    dispute_count = models.PositiveIntegerField(default=0)
    suspended_until = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["phone", "first_name", "last_name"]

    class Meta:
        ordering = ["-date_joined"]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name} <{self.email}>"

    def get_full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip() or self.email

    def get_short_name(self) -> str:
        return self.first_name or self.email

    @property
    def is_suspended(self) -> bool:
        return bool(self.suspended_until and self.suspended_until > timezone.now())

    @property
    def is_admin(self) -> bool:
        return self.is_staff or self.is_superuser


class OtpChallenge(UUIDModel):
    class Purpose(models.TextChoices):
        SIGNUP_EMAIL = "signup_email", "Signup email"
        SIGNUP_PHONE = "signup_phone", "Signup phone"
        LOGIN = "login", "Login"
        PHONE_CHANGE = "phone_change", "Phone change"
        EMAIL_CHANGE = "email_change", "Email change"
        PASSWORD_RESET = "password_reset", "Password reset"

    user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.CASCADE, related_name="otp_challenges"
    )
    purpose = models.CharField(max_length=32, choices=Purpose.choices)
    destination = models.CharField(max_length=255)
    code_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    attempt_count = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=5)
    consumed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class WorkerProfile(BaseModel):
    """Kept on accounts for existing migrations; Phase 1 documents live in workers app."""

    class VerificationStatus(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PENDING = "PENDING", "Pending"
        SUBMITTED = "SUBMITTED", "Submitted"
        VERIFIED = "VERIFIED", "Verified"
        REJECTED = "REJECTED", "Rejected"
        SUSPENDED = "SUSPENDED", "Suspended"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="worker_profile")
    display_name = models.CharField(max_length=120, blank=True)
    bio = models.TextField(blank=True)
    years_experience = models.PositiveSmallIntegerField(null=True, blank=True)
    id_number_encrypted = models.TextField(blank=True)
    id_number_masked = models.CharField(max_length=32, blank=True)
    id_document_type = models.CharField(max_length=32, blank=True)  # sa_id | passport | asylum_permit | refugee_id
    proof_of_address_url = models.URLField(blank=True)
    bank_account_masked = models.CharField(max_length=32, blank=True)
    bank_verified = models.BooleanField(default=False)
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.DRAFT,
    )
    rejection_reason = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_worker_profiles",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    hourly_rate_min_cents = models.PositiveIntegerField(null=True, blank=True)
    is_available = models.BooleanField(default=False)
    available_from = models.CharField(max_length=5, blank=True)
    available_to = models.CharField(max_length=5, blank=True)
    service_radius_km = models.FloatField(default=15)
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)
    city = models.CharField(max_length=80, default="Cape Town")
    region = models.CharField(max_length=80, default="Western Cape")
    country = models.CharField(max_length=80, default="South Africa")
    women_preferred_opt_in = models.BooleanField(default=False)
    avg_rating = models.FloatField(default=0)
    rating_count = models.PositiveIntegerField(default=0)
    completed_jobs = models.PositiveIntegerField(default=0)

    def __str__(self) -> str:
        return f"WorkerProfile<{self.user_id}:{self.verification_status}>"

    @property
    def can_receive_payouts(self) -> bool:
        return (
            self.verification_status == self.VerificationStatus.VERIFIED
            and self.bank_verified
            and not self.user.is_suspended
        )
