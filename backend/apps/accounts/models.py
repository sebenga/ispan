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
        return self._create_user(email, password, **extra)


class User(UUIDModel, AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        CUSTOMER = "CUSTOMER", "Customer"
        WORKER = "WORKER", "Worker"
        ADMIN = "ADMIN", "Admin"

    email = models.EmailField(unique=True, db_index=True)
    phone = models.CharField(max_length=20, unique=True)
    role = models.CharField(max_length=20, choices=Role.choices)
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
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
    REQUIRED_FIELDS = ["phone", "first_name", "last_name", "role"]

    class Meta:
        ordering = ["-date_joined"]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name} <{self.email}>"

    @property
    def is_suspended(self) -> bool:
        return bool(self.suspended_until and self.suspended_until > timezone.now())


class WorkerProfile(BaseModel):
    class VerificationStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUBMITTED = "SUBMITTED", "Submitted"
        VERIFIED = "VERIFIED", "Verified"
        REJECTED = "REJECTED", "Rejected"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="worker_profile")
    bio = models.TextField(blank=True)
    id_number_encrypted = models.CharField(max_length=255, blank=True)
    proof_of_address_url = models.URLField(blank=True)
    bank_account_masked = models.CharField(max_length=32, blank=True)
    bank_verified = models.BooleanField(default=False)
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
    )
    hourly_rate_min_cents = models.PositiveIntegerField(null=True, blank=True)
    is_available = models.BooleanField(default=False)
    available_from = models.CharField(max_length=5, blank=True)  # HH:MM
    available_to = models.CharField(max_length=5, blank=True)
    service_radius_km = models.FloatField(default=15)
    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)
    city = models.CharField(max_length=80, default="Cape Town")
    avg_rating = models.FloatField(default=0)
    rating_count = models.PositiveIntegerField(default=0)
    completed_jobs = models.PositiveIntegerField(default=0)

    def __str__(self) -> str:
        return f"WorkerProfile<{self.user_id}>"
