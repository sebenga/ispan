from __future__ import annotations

from django.db import models

from apps.accounts.models import WorkerProfile
from apps.core.models import BaseModel


class ServiceCategory(BaseModel):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=80)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children",
    )
    icon_key = models.CharField(max_length=40, blank=True)
    is_active = models.BooleanField(default=True)
    # Certificate.CertType values required before a worker may receive offers.
    min_certificate_types = models.JSONField(default=list, blank=True)
    commission_bps = models.PositiveIntegerField(default=1250)  # suggested start 12.5%
    cancel_fee_bps = models.PositiveIntegerField(default=5000)  # suggested start 50%
    cancel_window_minutes = models.PositiveIntegerField(default=120)
    suggested_min_cents = models.PositiveIntegerField()
    suggested_max_cents = models.PositiveIntegerField()
    sort_order = models.PositiveSmallIntegerField(default=100)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name_plural = "service categories"

    def __str__(self) -> str:
        return self.name

    @property
    def is_restricted(self) -> bool:
        return bool(self.min_certificate_types)


class WorkerService(BaseModel):
    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name="services")
    category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE, related_name="worker_services")
    price_cents = models.PositiveIntegerField()
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["worker", "category"], name="uniq_worker_category"),
        ]

    def __str__(self) -> str:
        return f"{self.worker_id}:{self.category.slug}"
