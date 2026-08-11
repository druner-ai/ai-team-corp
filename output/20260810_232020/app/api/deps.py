"""
Dependency injection for FastAPI routes.

Provides:
- Database session
- Redis client
- Service instances
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from app.db.session import get_db
from app.db.redis_client import get_redis
from app.repositories.url_repository import UrlRepository
from app.services.cache_service import CacheService
from app.services.code_generator import CodeGenerator
from app.services.url_service import UrlService


async def get_repository(
    session: AsyncSession = Depends(get_db),
) -> UrlRepository:
    """
    Dependency that provides a UrlRepository instance.

    Args:
        session: Async database session.

    Returns:
        UrlRepository instance.
    """
    return UrlRepository(session)


async def get_cache_service(
    redis: aioredis.Redis = Depends(get_redis),
) -> CacheService:
    """
    Dependency that provides a CacheService instance.

    Args:
        redis: Async Redis client.

    Returns:
        CacheService instance.
    """
    return CacheService(redis)


async def get_code_generator() -> CodeGenerator:
    """
    Dependency that provides a CodeGenerator instance.

    Returns:
        CodeGenerator instance.
    """
    return CodeGenerator()


async def get_url_service(
    repository: UrlRepository = Depends(get_repository),
    cache_service: CacheService = Depends(get_cache_service),
    code_generator: CodeGenerator = Depends(get_code_generator),
) -> UrlService:
    """
    Dependency that provides a fully initialized UrlService.

    Args:
        repository: URL repository.
        cache_service: Cache service.
        code_generator: Code generator.

    Returns:
        UrlService instance.
    """
    return UrlService(
        repository=repository,
        cache_service=cache_service,
        code_generator=code_generator,
    )