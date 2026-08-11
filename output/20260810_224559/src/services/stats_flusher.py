"""
Background task that periodically flushes click counters from Redis to PostgreSQL.

Uses an asyncio loop with a configurable interval (default 60 seconds).
"""
import asyncio
import logging

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import async_session_factory
from src.repositories.url_repository import UrlRepository
from src.services.stats_service import StatsService

logger = logging.getLogger(__name__)

FLUSH_INTERVAL = 60  # seconds


class StatsFlusher:
    """
    Asynchronous background task responsible for flushing Redis counters to the database.

    Should be started as a task during application lifespan and cancelled gracefully.
    """

    def __init__(self, redis: aioredis.Redis) -> None:
        self.redis = redis
        self.stats_service = StatsService(redis)
        self._task: asyncio.Task | None = None

    async def _flush_loop(self) -> None:
        """Infinite loop that flushes counters every FLUSH_INTERVAL seconds."""
        while True:
            await asyncio.sleep(FLUSH_INTERVAL)
            try:
                async with async_session_factory() as session:
                    repo = UrlRepository(session)
                    await self.stats_service.flush_counters(repo)
                    await session.commit()
                logger.debug("Flushed Redis counters to DB")
            except Exception:
                logger.exception("Error while flushing counters")

    async def start(self) -> None:
        """Start the flusher background task."""
        self._task = asyncio.create_task(self._flush_loop())
        logger.info("StatsFlusher started")

    async def stop(self) -> None:
        """Gracefully stop the flusher, performing a final flush."""
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        # Final flush before shutdown
        try:
            async with async_session_factory() as session:
                repo = UrlRepository(session)
                await self.stats_service.flush_counters(repo)
                await session.commit()
        except Exception:
            logger.exception("Error during final flush")
        logger.info("StatsFlusher stopped")