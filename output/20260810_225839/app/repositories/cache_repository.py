"""
Redis cache repository for short URL data and click counters.
"""
import redis.asyncio as aioredis
from typing import Optional, Dict
from app.config import settings


class CacheRepository:
    """Redis operations for URL caching."""

    def __init__(self, client: aioredis.Redis):
        self.client = client
        self.ttl = settings.cache_ttl_seconds

    def _key(self, short_code: str) -> str:
        return f"url:{short_code}"

    async def get_cached_url(self, short_code: str) -> Optional[Dict[str, str]]:
        """Retrieve cached URL data from Redis hash."""
        data = await self.client.hgetall(self._key(short_code))
        if data:
            return {
                key.decode(): value.decode() for key, value in data.items()
            }
        return None

    async def set_cached_url(
        self,
        short_code: str,
        original_url: str,
        created_at: str,
        expires_at: Optional[str] = None,
        is_deleted: bool = False,
    ) -> None:
        """Save URL data into Redis hash with TTL."""
        key = self._key(short_code)
        mapping = {
            "original_url": original_url,
            "created_at": created_at,
            "is_deleted": str(int(is_deleted)),
        }
        if expires_at:
            mapping["expires_at"] = expires_at
        await self.client.hset(key, mapping=mapping)
        await self.client.expire(key, self.ttl)

    async def delete_cached_url(self, short_code: str) -> None:
        """Remove a cached URL entry."""
        await self.client.delete(self._key(short_code))

    async def increment_click(self, short_code: str) -> None:
        """Increment click counter and set last_clicked_at in Redis (for cache hits)."""
        key = self._key(short_code)
        await self.client.hincrby(key, "clicks", 1)
        # Set last_clicked_at to current ISO timestamp
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        await self.client.hset(key, "last_clicked_at", now)