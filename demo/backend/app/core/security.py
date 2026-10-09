from __future__ import annotations

import math
import secrets
import threading
import time
from collections import deque
from dataclasses import dataclass

from fastapi import HTTPException, Request, Response, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import settings


api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(provided_key: str | None = Security(api_key_header)) -> None:
    if not settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API key authentication is not configured on the server",
        )
    if provided_key is None or not secrets.compare_digest(provided_key, settings.api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )


@dataclass(frozen=True, slots=True)
class RateLimitResult:
    allowed: bool
    remaining: int
    retry_after: int


class FixedWindowRateLimiter:
    """Thread-safe in-memory request limiter keyed by authenticated client."""

    def __init__(self, requests: int, window_seconds: int) -> None:
        if requests <= 0 or window_seconds <= 0:
            raise ValueError("Rate-limit requests and window must be positive")
        self.requests = requests
        self.window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def consume(self, key: str, now: float | None = None) -> RateLimitResult:
        current = time.monotonic() if now is None else now
        cutoff = current - self.window_seconds
        with self._lock:
            history = self._requests.setdefault(key, deque())
            while history and history[0] <= cutoff:
                history.popleft()
            if len(history) >= self.requests:
                retry_after = max(1, math.ceil(self.window_seconds - (current - history[0])))
                return RateLimitResult(False, 0, retry_after)
            history.append(current)
            remaining = self.requests - len(history)
            retry_after = max(1, math.ceil(self.window_seconds - (current - history[0])))
            return RateLimitResult(True, remaining, retry_after)


rate_limiter = FixedWindowRateLimiter(
    settings.rate_limit_requests,
    settings.rate_limit_window_seconds,
)


async def enforce_rate_limit(request: Request, response: Response) -> None:
    client_host = request.client.host if request.client else "unknown"
    result = rate_limiter.consume(client_host)
    headers = {
        "X-RateLimit-Limit": str(settings.rate_limit_requests),
        "X-RateLimit-Remaining": str(result.remaining),
        "X-RateLimit-Reset": str(result.retry_after),
    }
    if not result.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={**headers, "Retry-After": str(result.retry_after)},
        )
    response.headers.update(headers)
