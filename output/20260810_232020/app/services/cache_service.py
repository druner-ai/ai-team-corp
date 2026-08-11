"""
Redis cache service for URL caching and click counting.

Provides:
- URL caching with TTL (24 hours)
- Click counting via Redis Hash
- Cache invalidation
- Graceful degradation when Redis is unavailable
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """
    Service for Redis cache operations.

    Handles caching of URL mappings and click statistics.
    Implements circuit breaker pattern for Redis unavailability.
    """

    # Redis key patterns
    URL_KEY_PREFIX = "url:"
    STATS_KEY_PREFIX = "stats:"

    def __init__(self, redis_client: aioredis.Redis):
        """
        Initialize the cache service.

        Args:
            redis_client: Async Redis client instance.
        """
        self.redis = redis_client
        self._circuit_open = False
        self._failure_count = 0
        self._failure_threshold = 3
        self._timeout = 1.0  # 1 second timeout as per spec

    async def _execute_with_fallback(self, operation, fallback_value=None):
        """
        Execute a Redis operation with circuit breaker and fallback.

        Args:
            operation: Async callable that performs the Redis operation.
            fallback_value: Value to return if Redis is unavailable.

        Returns:
            Result of operation or fallback_value.
        """
        if self._circuit_open:
            return fallback_value

        try:
            result = await asyncio.wait_for(operation(), timeout=self._timeout)
            self._failure_count = 0
            return result
        except (asyncio.TimeoutError, Exception) as e:
            self._failure_count += 1
            logger.warning(f"Redis operation failed: {e}")

            if self._failure_count >= self._failure_threshold:
                self._circuit_open = True
                logger.error("Circuit breaker opened for Redis")

            return fallback_value

    async def cache_url(self, short_code: str, original_url: str) -> bool:
        """
        Cache a URL mapping in Redis with TTL.

        Args:
            short_code: The short code.
            original_url: The original URL.

        Returns:
            True if cached successfully, False otherwise.
        """
        key = f"{self.URL_KEY_PREFIX}{short_code}"

        async def _set():
            await self.redis.setex(key, settings.cache_ttl_seconds, original_url)
            return True

        result = await self._execute_with_fallback(_set, fallback_value=False)
        return result is True

    async def get_cached_url(self, short_code: str) -> Optional[str]:
        """
        Retrieve a cached URL by short code.

        Args:
            short_code: The short code to look up.

        Returns:
            Original URL if cached, None otherwise.
        """
        key = f"{self.URL_KEY_PREFIX}{short_code}"

        async def _get():
            return await self.redis.get(key)

        return await self._execute_with_fallback(_get)

    async def invalidate_cache(self, short_code: str) -> bool:
        """
        Remove a URL from cache.

        Args:
            short_code: The short code to invalidate.

        Returns:
            True if invalidated, False otherwise.
        """
        key = f"{self.URL_KEY_PREFIX}{short_code}"

        async def _delete():
            await self.redis.delete(key)
            return True

        result = await self._execute_with_fallback(_delete, fallback_value=False)
        return result is True

    async def increment_clicks(self, short_code: str) -> int:
        """
        Increment the click counter for a short code.

        Uses Redis HINCRBY for atomic increment.

        Args:
            short_code: The short code.

        Returns:
            New click count, or -1 if Redis is unavailable.
        """
        stats_key = f"{self.STATS_KEY_PREFIX}{short_code}"

        async def _increment():
            pipe = self.redis.pipeline()
            pipe.hincrby(stats_key, "clicks", 1)
            pipe.hset(
                stats_key,
                "last_accessed",
                datetime.now(timezone.utc).isoformat(),
            )
            results = await pipe.execute()
            return int(results[0])

        result = await self._execute_with_fallback(_increment, fallback_value=-1)
        return result if result != -1 else -1

    async def get_stats(self, short_code: str) -> dict:
        """
        Get click statistics for a short code.

        Args:
            short_code: The short code.

        Returns:
            Dict with 'clicks' and 'last_accessed', or empty dict if unavailable.
        """
        stats_key = f"{self.STATS_KEY_PREFIX}{short_code}"

        async def _get():
            return await self.redis.hgetall(stats_key)

        result = await self._execute_with_fallback(_get, fallback_value={})
        return result if result else {}

    async def is_healthy(self) -> bool:
        """
        Check if Redis connection is healthy.

        Returns:
            True if Redis is responsive, False otherwise.
        """
        try:
            await asyncio.wait_for(self.redis.ping(), timeout=self._timeout)
            return True
        except Exception:
            return False