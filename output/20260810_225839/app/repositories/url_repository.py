"""
Repository for PostgreSQL URL operations.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.url import URLRecord
from typing import Optional, List


class URLRepository:
    """CRUD operations for the `urls` table."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        short_code: str,
        original_url: str,
        expires_at: Optional[datetime] = None,
    ) -> URLRecord:
        """Create a new URL record and return it."""
        record = URLRecord(
            short_code=short_code,
            original_url=original_url,
            expires_at=expires_at,
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def get_by_short_code(self, short_code: str) -> Optional[URLRecord]:
        """Fetch a URL record by short_code (active and not deleted)."""
        stmt = select(URLRecord).where(
            URLRecord.short_code == short_code,
            URLRecord.is_deleted == False,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_click_and_last_access(self, record: URLRecord) -> None:
        """Atomically increment click_count and set last_clicked_at for a loaded record."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(URLRecord)
            .where(URLRecord.id == record.id)
            .values(
                click_count=URLRecord.click_count + 1,
                last_clicked_at=now,
            )
        )
        await self.session.execute(stmt)
        # Update the in-memory object as well
        record.click_count += 1
        record.last_clicked_at = now
        await self.session.commit()

    async def update_click_and_last_access_by_short_code(self, short_code: str, clicks: int) -> None:
        """
        Increment click_count by a specified amount and update last_clicked_at.
        Used during background sync.
        """
        now = datetime.now(timezone.utc)
        stmt = (
            update(URLRecord)
            .where(URLRecord.short_code == short_code)
            .values(
                click_count=URLRecord.click_count + clicks,
                last_clicked_at=now,
            )
        )
        await self.session.execute(stmt)

    async def soft_delete(self, record: URLRecord) -> None:
        """Mark the record as deleted."""
        record.is_deleted = True
        await self.session.commit()

    async def get_by_id(self, url_id: uuid.UUID) -> Optional[URLRecord]:
        """Fetch record by primary key (internal id)."""
        stmt = select(URLRecord).where(URLRecord.id == url_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def bulk_update_click_counts(self, updates: dict[str, int]) -> None:
        """
        Update click_count for multiple short_codes.
        Each value is the number of clicks to add.
        """
        for short_code, clicks in updates.items():
            stmt = (
                update(URLRecord)
                .where(URLRecord.short_code == short_code)
                .values(click_count=URLRecord.click_count + clicks)
            )
            await self.session.execute(stmt)
        await self.session.commit()