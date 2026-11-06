"""In-process pub/sub hub feeding the admin live stream.

Design (locked in Phase A / F20):
- Single process, asyncio queues — no external broker required.
- Fed by ``AuditService.log`` after a successful commit.
- Consumed by ``WS /api/v1/admin/stream?token=`` (auth via query token,
  accept-then-close with 4401/4403 on failure).
- Best effort: publishing never raises and never blocks the request path.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Slow consumers are disconnected instead of stalling audit writes.
_QUEUE_MAX = 256


class AdminEventHub:
    """Process-local subscriber registry for admin audit events."""

    _subscribers: set[asyncio.Queue[dict[str, Any]]] = set()

    @classmethod
    def subscribe(cls) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=_QUEUE_MAX)
        cls._subscribers.add(queue)
        return queue

    @classmethod
    def unsubscribe(cls, queue: asyncio.Queue[dict[str, Any]]) -> None:
        cls._subscribers.discard(queue)

    @classmethod
    def subscriber_count(cls) -> int:
        return len(cls._subscribers)

    @classmethod
    def publish(cls, event: dict[str, Any]) -> None:
        """Fan the event out to every subscriber. Never raises."""
        if not cls._subscribers:
            return
        slow: list[asyncio.Queue[dict[str, Any]]] = []
        for queue in list(cls._subscribers):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                slow.append(queue)
        for queue in slow:
            cls._subscribers.discard(queue)
            logger.warning("admin_event_hub_dropped_slow_consumer")
