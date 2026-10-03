"""Redis fixed-window rate limiting for the public tracking endpoints.

These endpoints are unauthenticated and enumerable by design, so we cap how
fast a single IP can hit them to blunt brute-forcing of tracking UUIDs/sigs.
"""
import logging

import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, Request, status

from app.config import settings

logger = logging.getLogger(__name__)

# One shared connection pool for the app process.
_redis = aioredis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)

TRACKING_LIMIT = 10  # requests
TRACKING_WINDOW_SECONDS = 60


async def _allow(key: str, limit: int, window_seconds: int) -> bool:
    """Increment the counter for `key`; set its TTL on first hit. Fails OPEN if
    Redis is unreachable so tracking still works in environments without it."""
    try:
        count = await _redis.incr(key)
        if count == 1:
            await _redis.expire(key, window_seconds)
        return count <= limit
    except Exception:
        logger.warning("Rate-limit check failed for %s; allowing request", key, exc_info=True)
        return True


def _client_ip(request: Request) -> str:
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip
    return request.client.host if request.client else "unknown"


async def rate_limit_tracking(request: Request) -> None:
    ip = _client_ip(request)
    # Bucket per fixed window so the key rolls over automatically.
    key = f"ratelimit:tracking:{ip}"
    if not await _allow(key, TRACKING_LIMIT, TRACKING_WINDOW_SECONDS):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests",
            headers={"Retry-After": str(TRACKING_WINDOW_SECONDS)},
        )


# Convenience export for use as a router/route dependency.
RateLimitTracking = Depends(rate_limit_tracking)
