"""
Statistics service for managing click counts.
Handles buffered stats in Redis and synchronization to PostgreSQL.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import logging

from app.models.url_mapping import UrlMapping
from app.services.cache_service import CacheService
from app.config import settings

logger = logging.getLogger(__name__)


class StatsService:
    """
    Service for managing URL click statistics.
    
    Buffers click counts in Redis and periodically syncs to PostgreSQL
    to reduce write load on the database during high traffic.
    
    Attributes:
        cache_service: Cache service for Redis operations
        sync_threshold: Number of clicks before syncing to DB
    """
    
    def __init__(
        self,
        cache_service: CacheService,
        sync_threshold: int | None = None
    ):
        """
        Initialize stats service.
        
        Args:
            cache_service: Cache service instance
            sync_threshold: Clicks threshold for DB sync (uses settings if not provided)
        """
        self.cache_service = cache_service
        self.sync_threshold = sync_threshold or settings.STATS_SYNC_THRESHOLD
    
    async def record_click(self, short_id: str, db_session: AsyncSession) -> None:
        """
        Record a click for a short URL.
        
        Increments counter in Redis and syncs to PostgreSQL
        when threshold is reached.
        
        Args:
            short_id: Short identifier
            db_session: Database session for potential sync
        """
        # Increment in Redis
        new_count = await self.cache_service.increment_stats(short_id)
        
        # Check if we should sync to PostgreSQL
        if new_count % self.sync_threshold == 0:
            await self.sync_to_db(short_id, db_session)
    
    async def sync_to_db(self, short_id: str, db_session: AsyncSession) -> None:
        """
        Synchronize click count from Redis to PostgreSQL.
        
        Args:
            short_id: Short identifier
            db_session: Database session
        """
        try:
            redis_count = await self.cache_service.get_stats(short_id)
            
            if redis_count > 0:
                stmt = (
                    update(UrlMapping)
                    .where(UrlMapping.short_id == short_id)
                    .values(click_count=redis_count)
                )
                await db_session.execute(stmt)
                await db_session.commit()
                
                logger.debug(f"Synced stats for {short_id}: {redis_count} clicks")
        except Exception as e:
            logger.error(f"Failed to sync stats for {short_id}: {e}")
            await db_session.rollback()
    
    async def get_total_clicks(self, short_id: str, db_session: AsyncSession) -> int:
        """
        Get total click count combining Redis buffer and DB value.
        
        Args:
            short_id: Short identifier
            db_session: Database session
            
        Returns:
            int: Total click count
        """
        # Get Redis buffer count
        redis_count = await self.cache_service.get_stats(short_id)
        
        # Get DB count
        stmt = select(UrlMapping.click_count).where(UrlMapping.short_id == short_id)
        result = await db_session.execute(stmt)
        db_count = result.scalar_one_or_none()
        
        if db_count is None:
            return redis_count
        
        # Return the maximum of both (Redis should be more up-to-date)
        return max(redis_count, db_count)
    
    async def cleanup_stats(self, short_id: str) -> None:
        """
        Remove stats from Redis for a deleted URL.
        
        Args:
            short_id: Short identifier
        """
        await self.cache_service.delete_stats(short_id)