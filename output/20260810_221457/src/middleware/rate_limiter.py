"""
    Sliding window rate limiter using Redis sorted set.
"""
import time
import logging
import uuid
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from fastapi import status

from src.dependencies import get_redis
from src.config import settings

logger = logging.getLogger(__name__)

class RateLimiterMiddleware(BaseHTTPMiddleware):
    EXCLUDED_PATHS = ["/health", "/ready", "/docs", "/redoc", "/openapi.json"]

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        if path in self.EXCLUDED_PATHS or path.startswith("/docs") or path.startswith("/redoc"):
            return await call_next(request)

        forwarded = request.headers.get("X-Forwarded-For")
        ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
        redis = await get_redis()
        if redis is None:
            return await call_next(request)  # Redis unavailable, skip rate limiting

        key = f"ratelimit:{ip}"
        now = time.time()
        window = 60
        max_requests = settings.RATE_LIMIT_PER_MINUTE

        try:
            # Remove outdated entries
            await redis.zremrangebyscore(key, 0, now - window)
            current = await redis.zcard(key)
            if current >= max_requests:
                retry_after = window
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": "Too many requests",
                            "request_id": getattr(request.state, "request_id", None),
                        }
                    },
                    headers={"Retry-After": str(retry_after)},
                )
            await redis.zadd(key, {str(uuid.uuid4()): now})
            await redis.expire(key, window)
        except Exception:
            logger.warning("Redis error in rate limiter, allowing request.", exc_info=True)
            # Allow request to proceed

        response = await call_next(request)
        return response