import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from app.core.config import settings

_store_lock = threading.Lock()
_windows: dict[str, deque] = defaultdict(deque)


def _key(request: Request, bucket: str) -> str:
    auth = request.headers.get("Authorization", "")
    identity = auth[:64] if auth else (request.client.host if request.client else "anon")
    return f"{bucket}:{identity}"


def check_rate_limit(request: Request, bucket: str, limit: int) -> None:
    now = time.time()
    key = _key(request, bucket)
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


def auth_rate_limit(request: Request) -> None:
    check_rate_limit(request, "auth", settings.rate_limit_auth_per_minute)


def api_rate_limit(request: Request) -> None:
    check_rate_limit(request, "api", settings.rate_limit_api_per_minute)
