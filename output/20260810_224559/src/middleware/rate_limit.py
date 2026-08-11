"""
Middleware implementing sliding window rate limiting using Redis Sorted Sets.

Rate limits are per client IP address.
"""
import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

from src.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding window rate limiter backed by Redis.

    Adds headers: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
    """

    def __init__(self, app, redis_client) -> None:
        super().__init__(app)
        self.redis = redis_client
        self.limit = settings.rate_limit_requests
        self.window = settings.rate_limit_window

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Exclude health check and docs from rate limiting
        if request.url.path in ("/health", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        key = f"ratelimit:{client_ip}"
        now = time.time()
        window_start = now - self.window

        # Atomic operations: add current request and remove old entries
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.zadd(key, {str(now): now})
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            pipe.expire(key, self.window + 10)  # extend TTL slightly
            _, _, current_count, _ = await pipe.execute()

        remaining = max(0, self.limit - current_count)
        reset_time = int(now + self.window)

        # Prepare headers
        headers = dict(request.headers)
        response_headers = {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(reset_time),
        }

        if current_count > self.limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please wait before retrying."},
                headers=response_headers,
            )

        response = await call_next(request)
        response.headers.update(response_headers)
        return response