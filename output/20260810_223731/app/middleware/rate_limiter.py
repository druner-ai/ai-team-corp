"""
ASGI middleware for rate limiting using Redis.
"""
import time
import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.redis_client import redis_client
from app.config import settings

logger = logging.getLogger(__name__)


async def check_rate_limit(client_ip: str) -> bool:
    """
    Check if the rate limit for the current minute bucket is exceeded.
    Returns True if allowed, False if limit reached.
    In case of Redis failures, logs a warning and allows the request (fail-open).
    """
    try:
        current_minute = int(time.time() / 60)
        key = f"ratelimit:{client_ip}:{current_minute}"

        # Atomic INCR and EXPIRE using pipeline
        async with redis_client.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.expire(key, 120)  # Keep the key for up to 2 minutes to avoid race
            results = await pipe.execute()
            count = results[0]  # INCR result

        if count > settings.RATE_LIMIT_PER_MINUTE:
            logger.warning("Rate limit exceeded for IP %s (count=%d)", client_ip, count)
            return False
        return True
    except Exception:
        logger.exception("Redis unavailable, rate limiting disabled")
        return True   # fail-open: allow request


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces per-IP rate limits.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host if request.client else "unknown"

        if not await check_rate_limit(client_ip):
            now = int(time.time())
            seconds_to_next = 60 - (now % 60)
            retry_after = max(1, seconds_to_next)
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."},
                headers={"Retry-After": str(retry_after)},
            )

        response = await call_next(request)
        return response