"""
Redis async client factory using redis.asyncio.
"""
import redis.asyncio as aioredis
from typing import AsyncIterator

from app.config import settings


async def get_redis_client() -> AsyncIterator[aioredis.Redis]:
    """
    Dependency that provides an async Redis connection.
    Uses a connection pool for efficiency.
    """
    pool = aioredis.ConnectionPool.from_url(settings.redis_url, max_connections=10)
    client = aioredis.Redis(connection_pool=pool)
    try:
        yield client
    finally:
        await client.close()
        await pool.disconnect()