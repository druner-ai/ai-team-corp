"""
    Redis async client factory and connection pool.
"""
import logging
from typing import Optional

import redis.asyncio as aioredis
from redis.asyncio.connection import ConnectionPool

from src.config import settings

logger = logging.getLogger(__name__)

pool: Optional[ConnectionPool] = None

async def create_redis_pool() -> Optional[ConnectionPool]:
    global pool
    if pool is not None:
        return pool
    try:
        pool = aioredis.ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=20,
        )
        logger.info("Redis connection pool created")
        return pool
    except Exception as e:
        logger.warning("Failed to create Redis pool: %s. Service will work without Redis cache.", e)
        pool = None
        return None

async def get_redis() -> Optional[aioredis.Redis]:
    """Returns Redis client or None if unavailable."""
    p = await create_redis_pool()
    if p is None:
        return None
    return aioredis.Redis(connection_pool=p)

async def close_redis_pool():
    global pool
    if pool:
        await pool.disconnect()
        pool = None