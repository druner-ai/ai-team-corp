"""
Service for click statistics and increment operations.
"""
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.url import URLRecord

logger = logging.getLogger(__name__)


async def get_stats(db_session: AsyncSession, short_id: str) -> Optional[URLRecord]:
    """Retrieve URLRecord and stats, or None if not found / deleted."""
    stmt = select(URLRecord).where(URLRecord.id == short_id, URLRecord.deleted == False)
    result = await db_session.execute(stmt)
    return result.scalar_one_or_none()


async def increment_clicks(db_session: AsyncSession, short_id: str) -> None:
    """
    Atomically increment the clicks counter for a given short URL.
    Designed to be used with a dedicated session.
    """
    stmt = (
        update(URLRecord)
        .where(URLRecord.id == short_id, URLRecord.deleted == False)
        .values(clicks=URLRecord.clicks + 1)
    )
    await db_session.execute(stmt)
    await db_session.commit()
    logger.debug("Incremented clicks for %s", short_id)