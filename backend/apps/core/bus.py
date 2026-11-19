"""Publish realtime envelopes to Redis for the Node Socket.io gateway."""

from __future__ import annotations

import json
import logging
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)


def publish_event(*, event: str, rooms: list[str], payload: dict[str, Any]) -> None:
    envelope = {"event": event, "rooms": rooms, "payload": payload}
    channel = getattr(settings, "REALTIME_EVENT_CHANNEL", "ispan:events")

    if getattr(settings, "REALTIME_POLLING", False):
        # Single-process Render free tier: clients poll REST instead.
        logger.debug("Realtime polling mode; skipped publish %s", event)
        return

    try:
        import redis

        client = redis.from_url(settings.REDIS_URL)
        client.publish(channel, json.dumps(envelope, default=str))
    except Exception:
        logger.exception("Failed to publish realtime event %s", event)
