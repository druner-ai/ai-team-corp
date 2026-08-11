"""
Redis client management with connection pooling.
Provides async Redis client for caching, rate limiting, and stats buffering.
"""
import redis.asyncio as redis
from typing import Optional

from app.config import settings


# Global Redis connection pool
_redis_pool: Optional[redis.ConnectionPool] = None
_redis_client: Optional[redis.Redis] = None


async def get_redis_client() -> redis.Redis:
    """
    Get or create Redis client with connection pooling.
    
    Returns:
        redis.Redis: Configured async Redis client
        
    Note:
        Uses connection pool size of 10 as per architecture requirements.
        The client is created once and reused across requests.
    """
    global _redis_pool, _redis_client
    
    if _redis_client is None:
        _redis_pool = redis.ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=10,
            password=settings.REDIS_PASSWORD,
            decode_responses=True,
        )
        _redis_client = redis.Redis(connection_pool=_redis_pool)
    
    return _redis_client


async def close_redis() -> None:
    """
    Close Redis connection pool.
    Called during application shutdown.
    """
    global _redis_client, _redis_pool
    
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
    
    if _redis_pool:
        await _redis_pool.disconnect()
        _redis_pool = None