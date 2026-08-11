"""
Repository for URL CRUD operations.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.url import Url


class UrlRepository:
    """
    Repository for URL database operations.

    Provides async methods for CRUD operations on the urls table.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        short_code: str,
        original_url: str,
        expires_at: Optional[datetime] = None,
    ) -> Url:
        """
        Create a new shortened URL record.

        Args:
            short_code: The generated short code.
            original_url: The original long URL.
            expires_at: Optional expiration datetime.

        Returns:
            The created Url instance.
        """
        url = Url(
            short_code=short_code,
            original_url=original_url,
            expires_at=expires_at,
        )
        self.session.add(url)
        await self.session.commit()
        await self.session.refresh(url)
        return url

    async def get_by_short_code(self, short_code: str) -> Optional[Url]:
        """
        Retrieve a URL by its short code.

        Args:
            short_code: The short code to look up.

        Returns:
            Url instance if found, None otherwise.
        """
        result = await self.session.execute(
            select(Url).where(Url.short_code == short_code)
        )
        return result.scalar_one_or_none()

    async def get_active_by_short_code(self, short_code: str) -> Optional[Url]:
        """
        Retrieve an active (not deleted, not expired) URL by short code.

        Args:
            short_code: The short code to look up.

        Returns:
            Url instance if found and active, None otherwise.
        """
        result = await self.session.execute(
            select(Url).where(
                Url.short_code == short_code,
                Url.is_deleted == False,
                (Url.expires_at.is_(None)) | (Url.expires_at > datetime.now(timezone.utc)),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_original_url(self, original_url: str) -> Optional[Url]:
        """
        Find an existing URL by its original URL.

        Args:
            original_url: The original URL to search for.

        Returns:
            Url instance if found, None otherwise.
        """
        result = await self.session.execute(
            select(Url).where(
                Url.original_url == original_url,
                Url.is_deleted == False,
            )
        )
        return result.scalar_one_or_none()

    async def soft_delete(self, short_code: str) -> Optional[Url]:
        """
        Soft delete a URL by marking it as deleted.

        Args:
            short_code: The short code to delete.

        Returns:
            Updated Url instance if found, None otherwise.
        """
        url = await self.get_by_short_code(short_code)
        if url is None:
            return None

        url.is_deleted = True
        await self.session.commit()
        await self.session.refresh(url)
        return url

    async def increment_clicks(self, short_code: str) -> None:
        """
        Increment click counter for a URL.
        
        Note: This is a placeholder. Actual click counting is done in Redis.
        This method exists for potential future use or batch sync operations.

        Args:
            short_code: The short code to increment clicks for.
        """
        # Click counting is primarily handled in Redis via cache_service
        # This method is reserved for batch synchronization from Redis to PostgreSQL
        pass