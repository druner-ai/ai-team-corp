"""
Background service to synchronize click counts from Redis to PostgreSQL.
Runs at a configurable interval.
"""
import asyncio
import logging
from redis.asyncio import Redis
from app.repositories.url_repository import URLRepository
from app.config import settings
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


class SyncService:
    """Handles periodic sync of click counts from Redis to DB."""

    def __init__(self):
        self._task: asyncio.Task | None = None

    async def sync_clicks(self, redis: Redis, db_session_factory: async_sessionmaker) -> None:
        """
        Scan Redis hash keys matching 'url:*' and accumulate clicks,
        then batch-update the database.
        """
        try:
            cursor = 0
            updates: dict[str, int] = {}
            async for key in redis.scan_iter(match="url:*"):
                short_code = key.decode().split(":", 1)[1] if isinstance(key, bytes) else key.split(":", 1)[1]
                # Get clicks field and reset if present
                clicks_bytes = await redis.hget(key, "clicks")
                if clicks_bytes:
                    clicks = int(clicks_bytes)
                    if clicks > 0:
                        updates[short_code] = clicks
                        await redis.hdel(key, "clicks")  # reset after sync
            if not updates:
                return

            logger.info(f"Syncing click counts for {len(updates)} short codes.")
            async with db_session_factory() as session:
                repo = URLRepository(session)
                for code, clicks in updates.items():
                    # update individual rows; better to bulk but we use repository method
                    await repo.update_click_and_last_access_by_short_code(code, clicks)
                await session.commit()
        except Exception as e:
            logger.error(f"Error during click sync: {e}", exc_info=True)

    async def start(self, redis: Redis, db_session_factory: async_sessionmaker):
        """Start the periodic sync loop."""
        logger.info("Starting background click sync service.")
        while True:
            await asyncio.sleep(settings.sync_interval_seconds)
            await self.sync_clicks(redis, db_session_factory)

    async def stop(self):
        """Stop the background task if running."""
        if self._task and not self._task.cancelled():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass