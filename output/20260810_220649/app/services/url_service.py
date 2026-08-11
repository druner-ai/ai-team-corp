"""
Business logic for URL shortening, retrieval, stats, and deletion.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.config import settings
from app.core.short_id import generate_short_id
from app.models.url import Url


class UrlService:
    """Service handling all URL-related operations."""

    MAX_RETRIES = 5

    def __init__(self, session: AsyncSession):
        self.session = session

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    async def create_short_url(self, original_url: str, expires_at: Optional[datetime] = None) -> dict:
        """
        Create a new short URL record.
        Generates a unique short_id with retry on collision.
        Returns a dictionary suitable for ShortenResponse.
        """
        for attempt in range(self.MAX_RETRIES):
            short_id = generate_short_id(settings.short_id_length)
            # Check if it already exists (race condition possible, but we rely on unique constraint)
            exists = await self.session.execute(
                select(Url.short_id).where(Url.short_id == short_id)
            )
            if exists.scalar_one_or_none() is None:
                url_obj = Url(
                    id=uuid.uuid4(),
                    short_id=short_id,
                    original_url=original_url,
                    expires_at=expires_at,
                )
                self.session.add(url_obj)
                try:
                    await self.session.commit()
                except Exception:
                    await self.session.rollback()
                    if attempt < self.MAX_RETRIES - 1:
                        logger.warning(f"Collision on short_id {short_id}, retrying...")
                        continue
                    raise RuntimeError("Failed to create short URL after retries")
                await self.session.refresh(url_obj)
                return {
                    "short_id": url_obj.short_id,
                    "short_url": f"{settings.base_url}/{url_obj.short_id}",
                    "original_url": url_obj.original_url,
                    "created_at": url_obj.created_at,
                }
        raise RuntimeError("Exhausted retries for short ID generation")

    async def get_url(self, short_id: str) -> Optional[Url]:
        """
        Retrieve a URL object by short_id.
        """
        result = await self.session.execute(
            select(Url).where(Url.short_id == short_id)
        )
        return result.scalar_one_or_none()

    async def increment_click_count(self, short_id: str) -> None:
        """
        Increment click count and update last_accessed_at for a URL.
        This is intended to be called as a background task.
        Uses atomic update to avoid race conditions.
        """
        now = self._now()
        stmt = (
            update(Url)
            .where(Url.short_id == short_id)
            .values(
                click_count=Url.click_count + 1,
                last_accessed_at=now,
            )
        )
        await self.session.execute(stmt)
        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            logger.error(f"Failed to increment click count for {short_id}")

    async def soft_delete_url(self, short_id: str) -> None:
        """
        Soft delete a URL by setting is_active=False.
        """
        stmt = (
            update(Url)
            .where(Url.short_id == short_id)
            .values(is_active=False)
        )
        await self.session.execute(stmt)
        await self.session.commit()