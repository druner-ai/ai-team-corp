"""
URL service containing core business logic for URL shortening operations.
Orchestrates cache, database, and stats services.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import Optional, Tuple
import logging

from app.models.url_mapping import UrlMapping
from app.services.cache_service import CacheService
from app.services.stats_service import StatsService
from app.utils.short_id import generate_short_id, validate_short_id
from app.config import settings

logger = logging.getLogger(__name__)

# Maximum attempts to generate unique short ID (collision avoidance)
MAX_GENERATION_ATTEMPTS = 3


class UrlService:
    """
    Core service for URL shortening operations.
    
    Handles creation, retrieval, statistics, and deletion of short URLs.
    Coordinates between cache, database, and statistics services.
    
    Attributes:
        cache_service: Cache service for Redis operations
        stats_service: Statistics service for click tracking
        short_id_length: Length of generated short IDs
    """
    
    def __init__(
        self,
        cache_service: CacheService,
        stats_service: StatsService,
        short_id_length: int | None = None
    ):
        """
        Initialize URL service.
        
        Args:
            cache_service: Cache service instance
            stats_service: Statistics service instance
            short_id_length: Length of short IDs (uses settings if not provided)
        """
        self.cache_service = cache_service
        self.stats_service = stats_service
        self.short_id_length = short_id_length or settings.SHORT_ID_LENGTH
    
    async def create_short_url(
        self,
        original_url: str,
        db_session: AsyncSession
    ) -> UrlMapping:
        """
        Create a new short URL mapping.
        
        Generates a unique short ID, stores the mapping in PostgreSQL,
        and caches it in Redis.
        
        Args:
            original_url: The original URL to shorten
            db_session: Database session
            
        Returns:
            UrlMapping: Created URL mapping entity
            
        Raises:
            ValueError: If unable to generate unique short ID after max attempts
        """
        # Try to generate unique short ID
        for attempt in range(MAX_GENERATION_ATTEMPTS):
            short_id = generate_short_id(self.short_id_length)
            
            # Check if short_id already exists
            stmt = select(UrlMapping).where(UrlMapping.short_id == short_id)
            result = await db_session.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing is None:
                # Unique ID found, create mapping
                url_mapping = UrlMapping(
                    short_id=short_id,
                    original_url=str(original_url),
                )
                db_session.add(url_mapping)
                await db_session.commit()
                await db_session.refresh(url_mapping)
                
                # Cache the new mapping
                await self.cache_service.set_url(short_id, str(original_url))
                
                logger.info(f"Created short URL: {short_id} -> {original_url}")
                return url_mapping
        
        # This should be extremely rare with 62^7 combinations
        logger.error("Failed to generate unique short ID after max attempts")
        raise ValueError("Unable to generate unique short ID. Please try again.")
    
    async def get_original_url(
        self,
        short_id: str,
        db_session: AsyncSession
    ) -> Optional[str]:
        """
        Get original URL for a short ID and record a click.
        
        Checks Redis cache first, falls back to PostgreSQL.
        Records click for statistics.
        
        Args:
            short_id: Short identifier
            db_session: Database session
            
        Returns:
            Optional[str]: Original URL if found and active, None otherwise
        """
        # Validate short_id format
        if not validate_short_id(short_id, self.short_id_length):
            return None
        
        # Try cache first
        cached_url = await self.cache_service.get_url(short_id)
        if cached_url:
            # Record click asynchronously (don't await to avoid slowing response)
            await self.stats_service.record_click(short_id, db_session)
            return cached_url
        
        # Cache miss, query database
        stmt = select(UrlMapping).where(
            UrlMapping.short_id == short_id,
            UrlMapping.is_active == True
        )
        result = await db_session.execute(stmt)
        url_mapping = result.scalar_one_or_none()
        
        if url_mapping is None:
            return None
        
        # Cache for future requests
        await self.cache_service.set_url(short_id, url_mapping.original_url)
        
        # Record click
        await self.stats_service.record_click(short_id, db_session)
        
        return url_mapping.original_url
    
    async def get_stats(
        self,
        short_id: str,
        db_session: AsyncSession
    ) -> Optional[dict]:
        """
        Get statistics for a short URL.
        
        Args:
            short_id: Short identifier
            db_session: Database session
            
        Returns:
            Optional[dict]: Statistics dict if found, None otherwise
        """
        # Validate short_id format
        if not validate_short_id(short_id, self.short_id_length):
            return None
        
        stmt = select(UrlMapping).where(UrlMapping.short_id == short_id)
        result = await db_session.execute(stmt)
        url_mapping = result.scalar_one_or_none()
        
        if url_mapping is None:
            return None
        
        # Get total clicks (combining Redis buffer and DB)
        total_clicks = await self.stats_service.get_total_clicks(short_id, db_session)
        
        return {
            "short_id": url_mapping.short_id,
            "original_url": url_mapping.original_url,
            "click_count": total_clicks,
            "created_at": url_mapping.created_at,
            "is_active": url_mapping.is_active,
        }
    
    async def delete_url(
        self,
        short_id: str,
        db_session: AsyncSession
    ) -> bool:
        """
        Soft delete a short URL (set is_active=False).
        
        Removes from Redis cache and cleans up stats.
        
        Args:
            short_id: Short identifier
            db_session: Database session
            
        Returns:
            bool: True if deleted successfully, False if not found
        """
        # Validate short_id format
        if not validate_short_id(short_id, self.short_id_length):
            return False
        
        # Check if exists and is active
        stmt = select(UrlMapping).where(
            UrlMapping.short_id == short_id,
            UrlMapping.is_active == True
        )
        result = await db_session.execute(stmt)
        url_mapping = result.scalar_one_or_none()
        
        if url_mapping is None:
            return False
        
        # Soft delete
        url_mapping.is_active = False
        await db_session.commit()
        
        # Remove from cache
        await self.cache_service.delete_url(short_id)
        
        # Cleanup stats
        await self.stats_service.cleanup_stats(short_id)
        
        logger.info(f"Deleted short URL: {short_id}")
        return True