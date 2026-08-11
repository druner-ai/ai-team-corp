"""
Rate limiting middleware for FastAPI.
Integrates RateLimiter and applies to all routes (except health maybe).
"""
from typing import Callable, Awaitable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.rate_limiter import RateLimiter
from app.db.redis_client import get_redis
from app.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to apply rate limiting using Redis."""

    def __init__(
        self,
        app,
        redis_url: str,
        limit: int = settings.rate_limit_per_minute,
        exclude_paths: set = None
    ):
        super().__init__(app)
        self.redis_url = redis_url
        self.limit = limit
        self.exclude_paths = exclude_paths or {"/health", "/docs", "/redoc", "/openapi.json"}

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        # Skip rate limiting for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        client_ip = request.client.host
        redis = await get_redis()
        limiter = RateLimiter(redis, limit=self.limit)
        remaining = await limiter.is_rate_limited(client_ip)

        if remaining is None:
            # Rate limit exceeded
            return Response(
                content='{"detail":"Too many requests"}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": "60"}
            )

        response: Response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response