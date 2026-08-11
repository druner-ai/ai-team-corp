"""
FastAPI dependency injection.

Provides shared dependencies for database connections, services, and cache.
"""

from typing import AsyncGenerator

import aiosqlite

from app.config import settings
from app.repositories.database import DatabaseManager
from app.repositories.url_repository import URLRepository
from app.services.url_service import URLService
from app.cache.memory_cache import MemoryCache

# Global instances (initialized once at startup)
_db_manager: DatabaseManager | None = None
_cache: MemoryCache | None = None


def get_db_manager() -> DatabaseManager:
    """Return the global DatabaseManager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager(settings.database_path)
    return _db_manager


def get_cache() -> MemoryCache:
    """Return the global MemoryCache instance."""
    global _cache
    if _cache is None:
        _cache = MemoryCache(default_ttl=settings.cache_ttl_seconds)
    return _cache


async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """
    FastAPI dependency that yields a database connection.

    Uses the global DatabaseManager to get a connection.
    """
    db_manager = get_db_manager()
    async with db_manager.get_connection() as conn:
        yield conn


async def get_url_repository() -> URLRepository:
    """FastAPI dependency that provides a URLRepository instance."""
    db_manager = get_db_manager()
    return URLRepository(db_manager)


async def get_url_service() -> URLService:
    """FastAPI dependency that provides a URLService instance."""
    repository = await get_url_repository()
    cache = get_cache()
    return URLService(repository, cache, settings.base_url, settings.short_code_length)
