"""
Redis connection management. Provides a singleton Redis client.
"""
import asyncio
from redis.asyncio import Redis

from app.config import settings

_redis: Redis | None = None
_lock = asyncio.Lock()


async def get_redis() -> Redis:
    """
    Return the Redis client, creating it if necessary.
    """
    global _redis
    if _redis is None:
        async with _lock:
            if _redis is None:
                _redis = Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
                await _redis.ping()
    return _redis


async def close_redis() -> None:
    """
    Close the Redis connection.
    """
    global _redis
    if _redis is not None:
        await _redis.close()
        _redis = None