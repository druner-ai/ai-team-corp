"""
Dependency injection for database sessions and Redis connections.
"""
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionLocal  # sessionmaker
from app.db.redis_client import get_redis as _get_redis


async def get_db() -> AsyncIterator[AsyncSession]:
    """
    Yields an async database session and ensures rollback on errors.
    """
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


# For convenience, re-export redis as a dependency
# (Redis client is a singleton pool, not a per-request connection)
async def get_redis_client():
    return await _get_redis()