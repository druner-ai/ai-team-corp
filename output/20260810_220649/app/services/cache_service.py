"""
Redis cache service for URL redirects.
"""
from typing import Optional

from redis.asyncio import Redis

from app.config import settings


class CacheService:
    """Service for caching shortened URLs in Redis."""

    def __init__(self, redis: Redis):
        self.redis = redis

    def _cache_key(self, short_id: str) -> str:
        return f"url:{short_id}"

    async def get_cached_url(self, short_id: str) -> Optional[str]:
        """
        Get original URL from cache if present.
        """
        value = await self.redis.get(self._cache_key(short_id))
        if value is not None:
            return value.decode("utf-8")
        return None

    async def set_cached_url(self, short_id: str, original_url: str) -> None:
        """
        Store original URL in cache with TTL.
        """
        await self.redis.setex(
            self._cache_key(short_id),
            settings.cache_ttl_seconds,
            original_url,
        )

    async def invalidate_url(self, short_id: str) -> None:
        """
        Remove a cached URL (used on delete).
        """
        await self.redis.delete(self._cache_key(short_id))