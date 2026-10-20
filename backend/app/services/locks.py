"""Distributed locks for singleton background work.

Celery Beat may run more than one replica during rolling deploys, and broker
redelivery or the stale-run sweeper can dispatch the same run twice.  Redis
locks make scheduling and execution idempotent.  If Redis is unavailable the
locks fail open and log a warning; the per-monitor active-run check and the
terminal-status guard remain as secondary defenses.
"""

from __future__ import annotations

import logging
import uuid

from app.core.config import settings

logger = logging.getLogger("release_guardian.locks")

SCHEDULER_LOCK_KEY = "rg:lock:scheduler"
SCHEDULER_LOCK_TTL_SECONDS = 55
RUN_LOCK_TTL_SECONDS = 900

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


def _acquire(key: str, ttl: int) -> tuple[bool, str | None]:
    token = uuid.uuid4().hex
    try:
        acquired = _client().set(key, token, nx=True, ex=ttl)
    except Exception as exc:  # noqa: BLE001 - never block work on a Redis outage
        logger.warning("lock_unavailable", extra={"key": key, "error": str(exc)[:200]})
        return True, None

    if not acquired:
        logger.info("lock_held", extra={"key": key})
        return False, None
    return True, token


def _release(key: str, token: str | None) -> None:
    if token is None:
        return
    try:
        _client().eval(_RELEASE_SCRIPT, 1, key, token)
    except Exception as exc:  # noqa: BLE001 - the lock expires via TTL
        logger.warning("unlock_failed", extra={"key": key, "error": str(exc)[:200]})


def acquire_scheduler_lock(ttl: int = SCHEDULER_LOCK_TTL_SECONDS) -> tuple[bool, str | None]:
    """Try to acquire the singleton scheduler lock."""
    if settings.worker_mode != "celery":
        return True, None
    return _acquire(SCHEDULER_LOCK_KEY, ttl)


def release_scheduler_lock(token: str | None) -> None:
    if settings.worker_mode != "celery":
        return
    _release(SCHEDULER_LOCK_KEY, token)


def acquire_run_lock(
    run_id: str, ttl: int = RUN_LOCK_TTL_SECONDS
) -> tuple[bool, str | None]:
    """Try to become the single executor for ``run_id``."""
    if settings.worker_mode != "celery":
        return True, None
    return _acquire(f"rg:lock:run:{run_id}", ttl)


def release_run_lock(run_id: str, token: str | None) -> None:
    if settings.worker_mode != "celery":
        return
    _release(f"rg:lock:run:{run_id}", token)
