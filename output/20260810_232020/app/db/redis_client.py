"""
Redis connection pool and client management.
"""

import redis.asyncio as aioredis
from typing import Optional

from app.config import settings

# Global Redis connection pool
_redis_pool: Optional[aioredis.ConnectionPool] = None
_redis_client: Optional[aioredis.Redis] = None


async def get_redis_pool() -> aioredis.ConnectionPool:
    """
    Get or create the Redis connection pool.

    Returns:
        aioredis.ConnectionPool: The Redis connection pool.
    """
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.ConnectionPool.from_url(
            settings.redis_url,
            max_connections=50,
            decode_responses=True,
        )
    return _redis_pool


async def get_redis() -> aioredis.Redis:
    """
    Dependency that provides a Redis client.

    Returns:
        aioredis.Redis: Redis client instance.

    Note:
        Uses a connection pool for efficiency.
    """
    pool = await get_redis_pool()
    return aioredis.Redis(connection_pool=pool)


async def close_redis_pool() -> None:
    """Close the Redis connection pool gracefully."""
    global _redis_pool, _redis_client
    if _redis_pool:
        await _redis_pool.disconnect()
        _redis_pool = None
        _redis_client = None