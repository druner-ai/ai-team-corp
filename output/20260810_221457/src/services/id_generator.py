"""
    Unique ID generation with collision retry.
"""
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models.url_mapping import UrlMapping
from src.utils.base62 import generate_random_id

logger = logging.getLogger(__name__)
MAX_RETRIES = 3

async def generate_unique_id(db: AsyncSession, length: int = 7) -> str:
    """Generate a unique short ID, retrying on collision."""
    for attempt in range(MAX_RETRIES):
        short_id = generate_random_id(length)
        stmt = select(UrlMapping.id).where(UrlMapping.id == short_id)
        result = await db.execute(stmt)
        if result.scalar() is None:
            return short_id
        logger.warning(f"ID collision for {short_id}, retry {attempt + 1}")
    raise RuntimeError("Failed to generate unique ID after multiple attempts")