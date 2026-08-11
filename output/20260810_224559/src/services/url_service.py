"""
Core business logic for URL shortening and retrieval.

Handles short_id generation with retry, database saving, and caching.
"""
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.core.exceptions import ShortIDCollisionError, URLNotFoundError
from src.repositories.url_repository import UrlRepository
from src.services.cache_service import CacheService
from src.utils.short_id import generate_short_id

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


class UrlService:
    """
    URL shortening service containing business logic.
    """

    def __init__(self, session: AsyncSession, cache: CacheService) -> None:
        self.session = session
        self.cache = cache
        self.repository = UrlRepository(session)

    async def create_short_url(self, original_url: str) -> dict:
        """
        Create a short URL for the given original URL.

        Generates a unique short_id, persists to DB and caches in Redis.

        Raises:
            ShortIDCollisionError: if unable to generate a unique ID after max retries.
        """
        for attempt in range(1, MAX_RETRIES + 1):
            short_id = generate_short_id()
            # Check if short_id already exists in cache or DB
            if await self.cache.get(short_id):
                logger.warning("Short ID %s collision in cache, retrying (attempt %d)", short_id, attempt)
                continue
            existing = await self.repository.get_by_short_id(short_id)
            if existing:
                logger.warning("Short ID %s collision in DB, retrying (attempt %d)", short_id, attempt)
                continue
            # Success
            now = datetime.now(timezone.utc)
            url_obj = await self.repository.create(short_id, original_url, now)
            await self.cache.set(short_id, original_url, now)
            return {
                "short_id": short_id,
                "short_url": f"{settings.app_base_url}/{short_id}",
                "original_url": original_url,
                "created_at": now,
            }
        raise ShortIDCollisionError("Failed to generate unique short ID after maximum retries")

    async def get_original_url(self, short_id: str) -> str:
        """
        Retrieve the original URL for a given short_id.

        Checks cache first, then falls back to database.
        Raises URLNotFoundError if the URL is missing or deleted.
        """
        # Cache lookup
        cached = await self.cache.get(short_id)
        if cached:
            return cached["original_url"]

        # Database lookup
        url_obj = await self.repository.get_by_short_id(short_id)
        if not url_obj or url_obj.is_deleted():
            raise URLNotFoundError(f"URL with id '{short_id}' not found")

        # Populate cache for next requests
        await self.cache.set(short_id, url_obj.original_url, url_obj.created_at)
        return url_obj.original_url

    async def delete_url(self, short_id: str) -> None:
        """
        Soft-delete a shortened URL by its short_id.

        Invalidates the cache entry.
        Raises URLNotFoundError if the URL does not exist or is already deleted.
        """
        url_obj = await self.repository.get_by_short_id(short_id)
        if not url_obj or url_obj.is_deleted():
            raise URLNotFoundError(f"URL with id '{short_id}' not found")
        await self.repository.soft_delete(url_obj.id)
        await self.cache.delete(short_id)

    async def get_stats(self, short_id: str) -> dict:
        """
        Retrieve statistics for a short URL.

        Raises URLNotFoundError if the URL is missing or deleted.
        """
        url_obj = await self.repository.get_by_short_id(short_id)
        if not url_obj or url_obj.is_deleted():
            raise URLNotFoundError(f"URL with id '{short_id}' not found")
        return {
            "short_id": url_obj.short_id,
            "original_url": url_obj.original_url,
            "click_count": url_obj.click_count,
            "created_at": url_obj.created_at,
            "last_clicked_at": url_obj.last_clicked_at,
        }