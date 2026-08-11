"""
Data access layer for URL entities using SQLAlchemy async.

Provides methods for CRUD operations and statistics updates.
"""
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.url import Url


class UrlRepository:
    """
    Repository for URL storage operations.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, short_id: str, original_url: str, created_at: datetime) -> Url:
        """Create and persist a new URL mapping."""
        url = Url(
            short_id=short_id,
            original_url=original_url,
            created_at=created_at,
        )
        self.session.add(url)
        await self.session.flush()  # to get id if needed
        return url

    async def get_by_short_id(self, short_id: str) -> Url | None:
        """Retrieve a URL entity by its short_id."""
        stmt = select(Url).where(Url.short_id == short_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def soft_delete(self, url_id: UUID) -> None:
        """Mark a URL as deleted by setting deleted_at."""
        now = datetime.now(timezone.utc)
        stmt = update(Url).where(Url.id == url_id).values(deleted_at=now)
        await self.session.execute(stmt)

    async def increment_clicks(self, short_id: str, amount: int) -> None:
        """Increment click_count and update last_clicked_at."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(Url)
            .where(Url.short_id == short_id)
            .values(click_count=Url.click_count + amount, last_clicked_at=now)
        )
        await self.session.execute(stmt)