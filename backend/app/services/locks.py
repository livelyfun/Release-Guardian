"""Distributed locks for singleton background work.

Celery Beat may run more than one replica during rolling deploys.  A Redis
lock prevents two schedulers from enqueuing the same due monitors in the same
window.  If Redis is unavailable the lock fails open and logs a warning; the
per-monitor active-run check remains as a second line of defense.
"""

from __future__ import annotations

import logging
import uuid

from app.core.config import settings

logger = logging.getLogger("release_guardian.locks")

SCHEDULER_LOCK_KEY = "rg:lock:scheduler"
SCHEDULER_LOCK_TTL_SECONDS = 55

_RELEASE_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
end
return 0
"""


def _client():
    import redis

    return redis.Redis.from_url(
        settings.redis_url, socket_connect_timeout=1, socket_timeout=1
    )


def acquire_scheduler_lock(ttl: int = SCHEDULER_LOCK_TTL_SECONDS) -> tuple[bool, str | None]:
    """Try to acquire the scheduler lock. Returns (acquired, token)."""
    if settings.worker_mode != "celery":
        return True, None

    token = uuid.uuid4().hex
    try:
        acquired = _client().set(SCHEDULER_LOCK_KEY, token, nx=True, ex=ttl)
    except Exception as exc:  # noqa: BLE001 - never block scheduling on Redis outage
        logger.warning("scheduler_lock_unavailable", extra={"error": str(exc)[:200]})
        return True, None

    if not acquired:
        logger.info("scheduler_lock_held")
        return False, None
    return True, token


def release_scheduler_lock(token: str | None) -> None:
    if token is None or settings.worker_mode != "celery":
        return
    try:
        _client().eval(_RELEASE_SCRIPT, 1, SCHEDULER_LOCK_KEY, token)
    except Exception as exc:  # noqa: BLE001 - lock expires via TTL
        logger.warning("scheduler_unlock_failed", extra={"error": str(exc)[:200]})
