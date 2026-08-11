"""
Service for managing click counters via Redis.

Increments a Redis counter and provides periodic flushing to the database.
"""
import asyncio

import redis.asyncio as aioredis

from src.repositories.url_repository import UrlRepository


class StatsService:
    """
    Handles click counting using Redis INCR.

    Counter key: `counter:{short_id}`
    """

    def __init__(self, redis: aioredis.Redis) -> None:
        self.redis = redis

    async def _counter_key(self, short_id: str) -> str:
        return f"counter:{short_id}"

    async def increment_click(self, short_id: str) -> None:
        """Increment the click counter for a given short_id asynchronously."""
        key = await self._counter_key(short_id)
        await self.redis.incr(key)

    async def get_pending_counts(self) -> dict[str, int]:
        """
        Retrieve all pending counter values from Redis.

        Returns:
            Mapping of short_id to click count (since last flush).
        """
        keys = await self.redis.keys("counter:*")
        if not keys:
            return {}
        values: list[int] = await self.redis.mget(keys)
        # Extract short_id from key pattern 'counter:{short_id}'
        result = {}
        for key_bytes, value in zip(keys, values):
            short_id = key_bytes.decode().split(":", 1)[1]
            count = int(value) if value else 0
            result[short_id] = count
        return result

    async def flush_counters(self, repository: UrlRepository) -> None:
        """
        Flush Redis counters to PostgreSQL and reset them.

        This is called periodically by the StatsFlusher background task.
        """
        pending = await self.get_pending_counts()
        for short_id, clicks in pending.items():
            if clicks > 0:
                await repository.increment_clicks(short_id, clicks)
                # Reset the counter in Redis
                key = await self._counter_key(short_id)
                await self.redis.set(key, 0)