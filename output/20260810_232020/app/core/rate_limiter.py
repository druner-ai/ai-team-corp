"""
Rate limiting configuration using slowapi with Redis backend.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from fastapi import FastAPI

from app.config import settings


def create_limiter() -> Limiter:
    """
    Create and configure the rate limiter.

    Returns:
        Configured Limiter instance with Redis storage.
    """
    limiter = Limiter(
        key_func=get_remote_address,
        storage_uri=settings.redis_url,
        default_limits=[settings.rate_limit_default],
    )
    return limiter


def setup_rate_limiting(app: FastAPI, limiter: Limiter) -> None:
    """
    Set up rate limiting middleware and exception handlers.

    Args:
        app: FastAPI application instance.
        limiter: Configured Limiter instance.
    """
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)