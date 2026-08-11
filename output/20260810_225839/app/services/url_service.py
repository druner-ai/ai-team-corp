"""
Business logic service for URL shortening, redirect, stats, and deletion.
Orchestrates repository and cache operations.
"""
from datetime import datetime, timezone
from typing import Optional
from app.repositories.url_repository import URLRepository
from app.repositories.cache_repository import CacheRepository
from app.services.short_code_generator import generate_code
from app.config import settings
from app.exceptions.handlers import (
    URLNotFoundError,
    URLDeletedError,
    URLExpiredError,
    ShortCodeGenerationError,
)


class URLService:
    """Service layer for URL shortener operations."""

    def __init__(
        self,
        url_repo: URLRepository,
        cache_repo: CacheRepository,
    ):
        self.url_repo = url_repo
        self.cache_repo = cache_repo

    async def shorten_url(
        self, original_url: str, expires_at: Optional[datetime] = None
    ) -> dict:
        """
        Create a short URL and return the data needed for the response.
        """
        # Generate unique short code with retries
        max_attempts = 5
        for _ in range(max_attempts):
            code = generate_code(settings.short_code_length)
            # Check if code already exists in DB (collision check)
            existing = await self.url_repo.get_by_short_code(code)
            if existing is None:
                break
        else:
            raise ShortCodeGenerationError(
                "Could not generate a unique short code after multiple attempts."
            )

        # Persist to database
        record = await self.url_repo.create(
            short_code=code,
            original_url=original_url,
            expires_at=expires_at,
        )

        # Cache the new URL data in Redis (prepare fields)
        await self.cache_repo.set_cached_url(
            short_code=code,
            original_url=record.original_url,
            created_at=record.created_at.isoformat(),
            expires_at=record.expires_at.isoformat() if record.expires_at else None,
            is_deleted=False,
        )

        return {
            "short_code": code,
            "short_url": f"{settings.base_url}/{code}",
            "original_url": record.original_url,
            "created_at": record.created_at,
            "expires_at": record.expires_at,
        }

    async def get_redirect_url(self, short_code: str) -> str:
        """
        Return the original URL for redirect, handling cache and error states.
        Raises exceptions for 404, 410.
        """
        # Check cache first
        cached = await self.cache_repo.get_cached_url(short_code)
        if cached:
            # Check deletion
            if cached.get("is_deleted") == "1":
                raise URLDeletedError()
            # Check expiration
            expires_at = cached.get("expires_at")
            if expires_at:
                try:
                    exp = datetime.fromisoformat(expires_at)
                    if exp.tzinfo is None:
                        exp = exp.replace(tzinfo=timezone.utc)
                    if datetime.now(timezone.utc) > exp:
                        raise URLExpiredError()
                except ValueError:
                    pass  # If parsing fails, treat as not expired
            # Cache hit: increment click in Redis (async, don't wait)
            await self.cache_repo.increment_click(short_code)
            return cached["original_url"]

        # Cache miss: query database
        record = await self.url_repo.get_by_short_code(short_code)
        if record is None:
            raise URLNotFoundError()
        if record.is_deleted:
            raise URLDeletedError()
        if record.expires_at and datetime.now(timezone.utc) > record.expires_at:
            raise URLExpiredError()

        # Populate cache (but don't wait for redirect)
        # Use asyncio.create_task? Should be fine to await since it's fast.
        await self.cache_repo.set_cached_url(
            short_code=record.short_code,
            original_url=record.original_url,
            created_at=record.created_at.isoformat(),
            expires_at=record.expires_at.isoformat() if record.expires_at else None,
            is_deleted=False,
        )

        # Increment click in DB (atomic update)
        await self.url_repo.update_click_and_last_access(record)

        return record.original_url

    async def get_stats(self, short_code: str) -> dict:
        """Return statistics for a short code."""
        record = await self.url_repo.get_by_short_code(short_code)
        if record is None:
            raise URLNotFoundError()

        # Determine active status
        is_active = not record.is_deleted
        if is_active and record.expires_at:
            is_active = datetime.now(timezone.utc) <= record.expires_at

        return {
            "short_code": record.short_code,
            "original_url": record.original_url,
            "created_at": record.created_at,
            "click_count": record.click_count,
            "last_clicked_at": record.last_clicked_at,
            "is_active": is_active,
        }

    async def delete_url(self, short_code: str) -> None:
        """Soft-delete a URL and clear its cache."""
        record = await self.url_repo.get_by_short_code(short_code)
        if record is None:
            raise URLNotFoundError()

        await self.url_repo.soft_delete(record)
        await self.cache_repo.delete_cached_url(short_code)