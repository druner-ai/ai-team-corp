"""
FastAPI dependency injection setup.
Provides database sessions, Redis clients, and service instances.
"""
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from app.db.session import get_db_session
from app.db.redis_client import get_redis_client
from app.services.cache_service import CacheService
from app.services.stats_service import StatsService
from app.services.url_service import UrlService


# Singleton service instances (created once, reused across requests)
_cache_service: CacheService | None = None
_stats_service: StatsService | None = None
_url_service: UrlService | None = None


async def get_cache_service(
    redis_client: redis.Redis = Depends(get_redis_client)
) -> CacheService:
    """
    Dependency that provides CacheService instance.
    
    Args:
        redis_client: Redis client from dependency
        
    Returns:
        CacheService: Configured cache service
    """
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService(redis_client)
    return _cache_service


async def get_stats_service(
    cache_service: CacheService = Depends(get_cache_service)
) -> StatsService:
    """
    Dependency that provides StatsService instance.
    
    Args:
        cache_service: Cache service from dependency
        
    Returns:
        StatsService: Configured stats service
    """
    global _stats_service
    if _stats_service is None:
        _stats_service = StatsService(cache_service)
    return _stats_service


async def get_url_service(
    cache_service: CacheService = Depends(get_cache_service),
    stats_service: StatsService = Depends(get_stats_service)
) -> UrlService:
    """
    Dependency that provides UrlService instance.
    
    Args:
        cache_service: Cache service from dependency
        stats_service: Stats service from dependency
        
    Returns:
        UrlService: Configured URL service
    """
    global _url_service
    if _url_service is None:
        _url_service = UrlService(cache_service, stats_service)
    return _url_service