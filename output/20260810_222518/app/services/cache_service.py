"""
Redis cache service for URL mappings and statistics.
Provides typed wrappers around Redis operations.
"""
import redis.asyncio as redis
from typing import Optional

from app.config import settings


class CacheService:
    """
    Service for Redis cache operations.
    
    Handles caching of URL mappings and provides typed interface
    for get/set/delete operations with proper key formatting.
    
    Attributes:
        redis_client: Async Redis client instance
        ttl: Default TTL for cache entries in seconds
    """
    
    # Key prefixes for different cache types
    URL_KEY_PREFIX = "url:"
    STATS_KEY_PREFIX = "stats:"
    RATE_LIMIT_KEY_PREFIX = "rl:"
    
    def __init__(self, redis_client: redis.Redis, ttl: int | None = None):
        """
        Initialize cache service.
        
        Args:
            redis_client: Async Redis client
            ttl: Default TTL in seconds (uses settings.CACHE_TTL_SECONDS if not provided)
        """
        self.redis_client = redis_client
        self.ttl = ttl or settings.CACHE_TTL_SECONDS
    
    def _url_key(self, short_id: str) -> str:
        """Format URL cache key."""
        return f"{self.URL_KEY_PREFIX}{short_id}"
    
    def _stats_key(self, short_id: str) -> str:
        """Format stats cache key."""
        return f"{self.STATS_KEY_PREFIX}{short_id}"
    
    async def get_url(self, short_id: str) -> Optional[str]:
        """
        Get cached original URL for a short ID.
        
        Args:
            short_id: Short identifier
            
        Returns:
            Optional[str]: Original URL if cached, None otherwise
        """
        return await self.redis_client.get(self._url_key(short_id))
    
    async def set_url(self, short_id: str, original_url: str, ttl: int | None = None) -> None:
        """
        Cache an original URL for a short ID.
        
        Args:
            short_id: Short identifier
            original_url: Original URL to cache
            ttl: Optional TTL override in seconds
        """
        key = self._url_key(short_id)
        await self.redis_client.setex(key, ttl or self.ttl, original_url)
    
    async def delete_url(self, short_id: str) -> None:
        """
        Remove cached URL for a short ID.
        
        Args:
            short_id: Short identifier
        """
        await self.redis_client.delete(self._url_key(short_id))
    
    async def increment_stats(self, short_id: str) -> int:
        """
        Increment click counter in Redis for a short ID.
        
        Args:
            short_id: Short identifier
            
        Returns:
            int: New counter value after increment
        """
        key = self._stats_key(short_id)
        return await self.redis_client.incr(key)
    
    async def get_stats(self, short_id: str) -> int:
        """
        Get current click count from Redis for a short ID.
        
        Args:
            short_id: Short identifier
            
        Returns:
            int: Current click count (0 if not found)
        """
        key = self._stats_key(short_id)
        value = await self.redis_client.get(key)
        return int(value) if value else 0
    
    async def delete_stats(self, short_id: str) -> None:
        """
        Remove stats counter from Redis for a short ID.
        
        Args:
            short_id: Short identifier
        """
        await self.redis_client.delete(self._stats_key(short_id))
    
    async def check_rate_limit(self, client_ip: str, limit: int = 100, window: int = 60) -> tuple[bool, int, int]:
        """
        Check rate limit for a client IP using sliding window.
        
        Args:
            client_ip: Client IP address
            limit: Maximum requests per window (default: 100)
            window: Time window in seconds (default: 60)
            
        Returns:
            tuple[bool, int, int]: (is_allowed, remaining, reset_time)
            - is_allowed: True if request is within limit
            - remaining: Number of requests remaining in window
            - reset_time: Unix timestamp when window resets
        """
        key = f"{self.RATE_LIMIT_KEY_PREFIX}{client_ip}"
        
        # Use Redis pipeline for atomic operations
        async with self.redis_client.pipeline() as pipe:
            current = await self.redis_client.get(key)
            
            if current is None:
                # First request in window
                await pipe.setex(key, window, 1)
                await pipe.ttl(key)
                results = await pipe.execute()
                return True, limit - 1, results[1]
            
            current_count = int(current)
            if current_count >= limit:
                # Rate limit exceeded
                ttl = await self.redis_client.ttl(key)
                return False, 0, ttl if ttl > 0 else window
            
            # Increment counter
            await pipe.incr(key)
            await pipe.ttl(key)
            results = await pipe.execute()
            new_count = results[0]
            ttl = results[1]
            
            return True, limit - new_count, ttl if ttl > 0 else window