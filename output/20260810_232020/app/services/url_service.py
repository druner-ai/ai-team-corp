"""
URL shortening business logic service.

Orchestrates the URL shortening workflow:
- URL validation
- Duplicate checking
- Short code generation
- Persistence and caching
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import (
    URLAlreadyDeletedException,
    URLAlreadyExistsException,
    URLExpiredException,
    URLNotFoundException,
)
from app.models.url import Url
from app.repositories.url_repository import UrlRepository
from app.services.cache_service import CacheService
from app.services.code_generator import CodeGenerator

logger = logging.getLogger(__name__)


class UrlService:
    """
    Service for URL shortening operations.

    Coordinates between repository, cache, and code generator
    to implement the business logic.
    """

    def __init__(
        self,
        repository: UrlRepository,
        cache_service: CacheService,
        code_generator: CodeGenerator,
    ):
        """
        Initialize the URL service.

        Args:
            repository: URL repository for database operations.
            cache_service: Cache service for Redis operations.
            code_generator: Code generator for creating short codes.
        """
        self.repository = repository
        self.cache = cache_service
        self.generator = code_generator

    async def shorten_url(self, original_url: str) -> dict:
        """
        Shorten a URL.

        Workflow:
        1. Check if URL already has a short code
        2. If yes, return existing code (409 Conflict)
        3. Generate new unique short code
        4. Save to database
        5. Cache in Redis
        6. Return response data

        Args:
            original_url: The validated original URL.

        Returns:
            Dict with short_code, short_url, original_url.

        Raises:
            URLAlreadyExistsException: If URL already shortened.
        """
        # Check for existing URL
        existing = await self.repository.get_by_original_url(original_url)
        if existing:
            raise URLAlreadyExistsException(
                short_code=existing.short_code,
                original_url=original_url,
            )

        # Generate unique short code
        # Use a simple incrementing counter based on current timestamp
        # In production, this should use a database sequence
        import time
        sequence_number = int(time.time() * 1000) % (10**10)

        def is_code_taken(code: str) -> bool:
            """Synchronous check for code availability."""
            # We'll check asynchronously in the actual flow
            return False

        short_code = self.generator.generate(sequence_number)

        # Verify uniqueness in database (with retry)
        for attempt in range(self.generator.MAX_RETRIES):
            existing_code = await self.repository.get_by_short_code(short_code)
            if not existing_code:
                break
            # Collision detected, generate new code
            sequence_number += 1000
            short_code = self.generator.generate(sequence_number)
        else:
            raise RuntimeError("Failed to generate unique short code")

        # Save to database
        url = await self.repository.create(
            short_code=short_code,
            original_url=original_url,
        )

        # Cache in Redis (fire and forget - don't block on cache failure)
        await self.cache.cache_url(short_code, original_url)

        # Build response
        short_url = f"{settings.base_url}/{short_code}"
        return {
            "short_code": short_code,
            "short_url": short_url,
            "original_url": original_url,
        }

    async def get_original_url(self, short_code: str) -> str:
        """
        Get the original URL for a short code and increment click counter.

        Workflow:
        1. Try Redis cache first
        2. On cache miss, query database
        3. Check if URL is deleted or expired
        4. Cache the result in Redis
        5. Increment click counter
        6. Return original URL

        Args:
            short_code: The short code to resolve.

        Returns:
            The original URL string.

        Raises:
            URLNotFoundException: If short code not found.
            URLAlreadyDeletedException: If URL is soft-deleted.
            URLExpiredException: If URL has expired.
        """
        # Try cache first
        cached_url = await self.cache.get_cached_url(short_code)
        if cached_url:
            # Increment click counter asynchronously
            await self.cache.increment_clicks(short_code)
            return cached_url

        # Cache miss - query database
        url = await self.repository.get_by_short_code(short_code)

        if url is None:
            raise URLNotFoundException(short_code)

        if url.is_deleted:
            raise URLAlreadyDeletedException(short_code)

        if url.expires_at and url.expires_at < datetime.now(timezone.utc):
            raise URLExpiredException(short_code)

        # Cache for future requests
        await self.cache.cache_url(short_code, url.original_url)

        # Increment click counter
        await self.cache.increment_clicks(short_code)

        return url.original_url

    async def get_stats(self, short_code: str) -> dict:
        """
        Get statistics for a short code.

        Combines data from database (original_url, created_at)
        and Redis (click count).

        Args:
            short_code: The short code.

        Returns:
            Dict with short_code, original_url, clicks, created_at.

        Raises:
            URLNotFoundException: If short code not found.
        """
        url = await self.repository.get_by_short_code(short_code)

        if url is None or url.is_deleted:
            raise URLNotFoundException(short_code)

        # Get click count from Redis
        redis_stats = await self.cache.get_stats(short_code)
        clicks = int(redis_stats.get("clicks", 0))

        return {
            "short_code": url.short_code,
            "original_url": url.original_url,
            "clicks": clicks,
            "created_at": url.created_at,
        }

    async def delete_url(self, short_code: str) -> None:
        """
        Soft delete a URL.

        Workflow:
        1. Check if URL exists
        2. Check if already deleted
        3. Soft delete in database
        4. Invalidate cache

        Args:
            short_code: The short code to delete.

        Raises:
            URLNotFoundException: If short code not found.
            URLAlreadyDeletedException: If already deleted.
        """
        url = await self.repository.get_by_short_code(short_code)

        if url is None:
            raise URLNotFoundException(short_code)

        if url.is_deleted:
            raise URLAlreadyDeletedException(short_code)

        # Soft delete
        await self.repository.soft_delete(short_code)

        # Invalidate cache
        await self.cache.invalidate_cache(short_code)