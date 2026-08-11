"""
Service for caching shortened URLs in Redis.

Stores JSON string with original_url and created_at.
"""
import json
from datetime import datetime
from typing import Any

import redis.asyncio as aioredis

from src.config import settings


class CacheService:
    """
    Manages the Redis cache for URL lookups.

    Cache key: `cache:{short_id}`
    Value: JSON with 'original_url' and 'created_at' (ISO format string).
    """

    def __init__(self, redis: aioredis.Redis) -> None:
        self.redis = redis
        self.ttl = settings.cache_ttl_seconds

    async def _cache_key(self, short_id: str) -> str:
        return f"cache:{short_id}"

    async def get(self, short_id: str) -> dict[str, Any] | None:
        """Retrieve cached data for a short_id."""
        key = await self._cache_key(short_id)
        data = await self.redis.get(key)
        if data is None:
            return None
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            await self.redis.delete(key)
            return None

    async def set(self, short_id: str, original_url: str, created_at: datetime) -> None:
        """Store URL data in the cache with TTL."""
        key = await self._cache_key(short_id)
        payload = {
            "original_url": original_url,
            "created_at": created_at.isoformat(),
        }
        await self.redis.set(key, json.dumps(payload), ex=self.ttl)

    async def delete(self, short_id: str) -> None:
        """Invalidate cached entry for a short_id."""
        key = await self._cache_key(short_id)
        await self.redis.delete(key)