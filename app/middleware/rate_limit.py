from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict
import time
from app.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Простейший in-memory rate limiter на основе IP."""

    def __init__(self, app, limit: int = settings.rate_limit_per_minute, window: int = 60):
        super().__init__(app)
        self.limit = limit
        self.window = window
        self.requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        # Удаляем устаревшие записи
        self.requests[client_ip] = [t for t in self.requests[client_ip] if now - t < self.window]
        if len(self.requests[client_ip]) >= self.limit:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        self.requests[client_ip].append(now)
        response = await call_next(request)
        return response
