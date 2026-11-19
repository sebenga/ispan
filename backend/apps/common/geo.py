"""Haversine helpers for MVP matching (PostGIS-ready later)."""

from __future__ import annotations

import math


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def bounding_box(lat: float, lng: float, radius_km: float) -> tuple[float, float, float, float]:
    """Return (min_lat, max_lat, min_lng, max_lng) approx for prefilter."""
    dlat = radius_km / 111.0
    cos_lat = max(math.cos(math.radians(lat)), 0.01)
    dlng = radius_km / (111.0 * cos_lat)
    return lat - dlat, lat + dlat, lng - dlng, lng + dlng
