from __future__ import annotations

from django.db import models

from apps.core.models import BaseModel


class MatchingConfig(BaseModel):
    """Admin-editable matching defaults (singleton row in practice)."""

    name = models.CharField(max_length=80, unique=True, default="default")
    initial_radius_km = models.FloatField(default=5)
    widen_step_km = models.FloatField(default=3)
    widen_interval_seconds = models.PositiveIntegerField(default=30)
    max_radius_km = models.FloatField(default=25)
    offer_seconds = models.PositiveIntegerField(default=20)
    max_concurrent_offers = models.PositiveIntegerField(default=8)
    rating_floor = models.FloatField(default=0)
    scheduled_match_lead_minutes = models.PositiveIntegerField(default=60)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "matching config"
        verbose_name_plural = "matching configs"

    def __str__(self) -> str:
        return self.name


def get_matching_config() -> MatchingConfig:
    cfg, _ = MatchingConfig.objects.get_or_create(name="default")
    return cfg
