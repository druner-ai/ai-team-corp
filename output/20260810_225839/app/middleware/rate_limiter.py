"""
Rate limiting configuration using slowapi with Redis backend.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.config import settings

# Limiter uses Redis storage for production-like behavior.
# For testing, we may swap storage to MemoryStorage.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],  # no default, we apply per-route
    storage_uri=settings.redis_url,  # slowapi's RedisStorage (sync)
)