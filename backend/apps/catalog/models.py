from __future__ import annotations

from django.db import models

from apps.accounts.models import WorkerProfile
from apps.core.models import BaseModel


class ServiceCategory(BaseModel):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=80)
    description = models.TextField(blank=True)
    suggested_min_cents = models.PositiveIntegerField()
    suggested_max_cents = models.PositiveIntegerField()

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "service categories"

    def __str__(self) -> str:
        return self.name


class WorkerService(BaseModel):
    worker = models.ForeignKey(WorkerProfile, on_delete=models.CASCADE, related_name="services")
    category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE, related_name="worker_services")
    price_cents = models.PositiveIntegerField()
    description = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["worker", "category"], name="uniq_worker_category"),
        ]

    def __str__(self) -> str:
        return f"{self.worker_id}:{self.category.slug}"
