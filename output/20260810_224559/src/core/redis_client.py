"""
Redis asynchronous client with connection pool.

Uses redis.asyncio module.
"""
import redis.asyncio as aioredis
from redis.asyncio import ConnectionPool

from src.config import settings

redis_pool: ConnectionPool = aioredis.ConnectionPool.from_url(
    settings.redis_url,
    max_connections=50,
)

redis_client: aioredis.Redis = aioredis.Redis(connection_pool=redis_pool)