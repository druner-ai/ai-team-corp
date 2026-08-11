"""
Sliding window rate limiter using Redis.
Implements a simple fixed-window counter as per architecture doc:
key rate:{ip}, TTL 60s, max requests per minute.
"""
from typing import Optional
import time

from redis.asyncio import Redis


class RateLimiter:
    """Rate limiter using Redis fixed-window counter."""

    def __init__(self, redis: Redis, limit: int = 100, window: int = 60):
        self.redis = redis
        self.limit = limit
        self.window = window

    async def is_rate_limited(self, client_ip: str) -> Optional[int]:
        """
        Check if client has exceeded the limit.
        Returns remaining requests if allowed, or None and sets Retry-After header time.
        """
        key = f"rate:{client_ip}"
        current = await self.redis.incr(key)
        if current == 1:
            await self.redis.expire(key, self.window)

        remaining = self.limit - current
        if remaining < 0:
            # Get TTL to calculate Retry-After
            ttl = await self.redis.ttl(key)
            return None  # blocked
        return remaining