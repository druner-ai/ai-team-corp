"""
Service for soft-deleting a short URL and clearing its cache.
"""
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.url import URLRecord
from app.services.url_service import invalidate_cache

logger = logging.getLogger(__name__)


async def soft_delete(db_session: AsyncSession, short_id: str) -> bool:
    """
    Mark URLRecord as deleted and invalidate Redis cache.

    Returns True if record existed and was deleted, False if not found.
    """
    record = await db_session.get(URLRecord, short_id)
    if not record or record.deleted:
        return False
    record.deleted = True
    await db_session.commit()
    # Invalidate cache
    await invalidate_cache(short_id)
    logger.info("Soft-deleted short URL id=%s", short_id)
    return True