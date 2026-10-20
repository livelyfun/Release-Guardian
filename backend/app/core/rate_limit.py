"""Global rate limiting with an optional shared Redis backend.

The in-memory window is per-process; with more than one API replica each
process would enforce its own quota.  ``RATE_LIMIT_BACKEND=auto`` (the default)
uses Redis whenever Celery mode is enabled and falls back to the in-memory
window if Redis is unreachable, so a broker outage never takes down the API.
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from app.core.config import settings

logger = logging.getLogger("release_guardian.rate_limit")

_store_lock = threading.Lock()
_windows: dict[str, deque] = defaultdict(deque)
_redis_client = None
_redis_next_attempt = 0.0


def _identity(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    raw = auth if auth else (request.client.host if request.client else "anon")
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _key(request: Request, bucket: str) -> str:
    return f"{bucket}:{_identity(request)}"


def _retry_after(now: float) -> int:
    return int(60 - (now % 60)) + 1


def _raise_limited(now: float) -> None:
    retry_after = _retry_after(now)
    raise HTTPException(
        status_code=429,
        detail=f"Rate limit exceeded. Retry-After: {retry_after}",
        headers={"Retry-After": str(retry_after)},
    )


def _memory_limit(key: str, limit: int, now: float) -> None:
    with _store_lock:
        window = _windows[key]
        while window and now - window[0] > 60.0:
            window.popleft()
        if len(window) >= limit:
            retry_after = int(60 - (now - window[0])) + 1
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Retry-After: {retry_after}",
                headers={"Retry-After": str(retry_after)},
            )
        window.append(now)


def _get_redis():
    global _redis_client, _redis_next_attempt
    if _redis_client is not None:
        return _redis_client
    now = time.time()
    if now < _redis_next_attempt:
        return None
    try:
        import redis

        client = redis.Redis.from_url(
            settings.redis_url, socket_connect_timeout=0.5, socket_timeout=0.5
        )
        client.ping()
        _redis_client = client
        return client
    except Exception as exc:  # noqa: BLE001 - fall back to per-process limits
        logger.warning("rate_limit_redis_unavailable", extra={"error": str(exc)[:200]})
        _redis_next_attempt = now + 30.0
        return None


def _redis_limit(client, key: str, limit: int, now: float) -> None:
    window_key = f"rg:rl:{key}:{int(now // 60)}"
    count = client.incr(window_key)
    if count == 1:
        client.expire(window_key, 61)
    if count > limit:
        _raise_limited(now)


def _use_redis() -> bool:
    backend = settings.rate_limit_backend.lower()
    if backend == "redis":
        return True
    if backend == "memory":
        return False
    return settings.worker_mode == "celery"


def check_rate_limit(request: Request, bucket: str, limit: int) -> None:
    now = time.time()
    key = _key(request, bucket)

    if _use_redis():
        client = _get_redis()
        if client is not None:
            try:
                _redis_limit(client, key, limit, now)
                return
            except HTTPException:
                raise
            except Exception as exc:  # noqa: BLE001 - degrade, do not fail open silently
                logger.warning(
                    "rate_limit_redis_error", extra={"error": str(exc)[:200]}
                )

    _memory_limit(key, limit, now)


def auth_rate_limit(request: Request) -> None:
    check_rate_limit(request, "auth", settings.rate_limit_auth_per_minute)


def api_rate_limit(request: Request) -> None:
    check_rate_limit(request, "api", settings.rate_limit_api_per_minute)
