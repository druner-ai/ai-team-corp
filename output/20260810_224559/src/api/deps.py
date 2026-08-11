"""
FastAPI dependency injection.

Provides async database sessions and Redis client to route handlers.
"""
from typing import AsyncGenerator

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import async_session_factory
from src.core.redis_client import redis_client


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session and ensure it's closed after use."""
    async with async_session_factory() as session:
        yield session


async def get_redis() -> aioredis.Redis:
    """Return the shared Redis client."""
    return redis_client