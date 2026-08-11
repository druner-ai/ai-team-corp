"""
GET /stats/{short_code} endpoint.
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_async_session
from app.services.url_service import URLService
from app.repositories.url_repository import URLRepository
from app.repositories.cache_repository import CacheRepository
from app.schemas.url import StatsResponse
from app.middleware.rate_limiter import limiter
from app.config import settings
from app.redis_client import get_redis_client
import redis.asyncio as aioredis

router = APIRouter()

@router.get(
    "/{short_code}",
    response_model=StatsResponse,
    summary="Get URL statistics",
    description="Returns click count, creation date, last click, and active status.",
)
@limiter.limit(settings.rate_limit_stats)
async def get_url_stats(
    request: Request,
    short_code: str,
    session: AsyncSession = Depends(get_async_session),
    redis: aioredis.Redis = Depends(get_redis_client),
):
    url_repo = URLRepository(session)
    cache_repo = CacheRepository(redis)
    service = URLService(url_repo, cache_repo)
    stats = await service.get_stats(short_code)
    return StatsResponse(**stats)