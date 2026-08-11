"""
Business logic for creating and retrieving short URLs.
"""
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.url import URLRecord
from app.utils.id_generator import generate_short_id
from app.redis_client import redis_client
from app.config import settings

logger = logging.getLogger(__name__)


async def create_short_url(db_session: AsyncSession, original_url: str) -> URLRecord:
    """Generate a unique short ID, create DB record, and return it."""
    max_attempts = 5
    for attempt in range(max_attempts):
        short_id = generate_short_id()
        existing = await db_session.get(URLRecord, short_id)
        if not existing:
            record = URLRecord(id=short_id, original_url=original_url)
            db_session.add(record)
            await db_session.commit()
            await db_session.refresh(record)
            logger.info("Created short URL: id=%s for url=%s", short_id, original_url[:50])
            return record
        logger.warning("Collision on short_id %s, attempt %d", short_id, attempt + 1)
    raise RuntimeError("Failed to generate unique short ID after multiple attempts")


async def get_original_url(db_session: AsyncSession, short_id: str) -> Optional[URLRecord]:
    """Fetch URLRecord from cache or database, populate cache on miss."""
    cache_key = f"cache:{short_id}"
    # Try Redis cache first (cached value is just the original_url string)
    cached_url = await redis_client.get(cache_key)
    if cached_url:
        logger.debug("Cache hit for %s", short_id)
        # Cache contains only the URL; we trust that the record is not deleted
        # because delete/invalidation removes this key.
        return URLRecord(id=short_id, original_url=cached_url, deleted=False)

    # Cache miss: query database
    stmt = select(URLRecord).where(URLRecord.id == short_id)
    result = await db_session.execute(stmt)
    record = result.scalar_one_or_none()
    if record and not record.deleted:
        # Populate cache
        await redis_client.set(cache_key, record.original_url, ex=settings.CACHE_TTL_SECONDS)
        return record
    return None


async def cache_url(short_id: str, original_url: str) -> None:
    """Store original_url in Redis cache."""
    await redis_client.set(f"cache:{short_id}", original_url, ex=settings.CACHE_TTL_SECONDS)


async def invalidate_cache(short_id: str) -> None:
    """Remove cached entry for given short ID."""
    await redis_client.delete(f"cache:{short_id}")