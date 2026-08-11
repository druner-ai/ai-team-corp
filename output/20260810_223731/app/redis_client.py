"""
Async Redis client with connection pool.
"""
import redis.asyncio as redis
from app.config import settings

# Create Redis connection pool
redis_pool = redis.ConnectionPool.from_url(
    settings.REDIS_URL,
    max_connections=50,
)

# Async Redis client
redis_client = redis.Redis(connection_pool=redis_pool)


async def get_redis() -> redis.Redis:
    """FastAPI dependency that provides a Redis client.

    The client is shared across requests (pool based).
    """
    return redis_client