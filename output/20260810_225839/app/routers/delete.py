"""
DELETE /{short_code} endpoint.
"""
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_async_session
from app.services.url_service import URLService
from app.repositories.url_repository import URLRepository
from app.repositories.cache_repository import CacheRepository
from app.middleware.rate_limiter import limiter
from app.config import settings
from app.redis_client import get_redis_client
import redis.asyncio as aioredis

router = APIRouter()

@router.delete(
    "/{short_code}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a short URL",
    description="Soft-deletes the short URL. Returns 204 if successful, 404 if not found.",
)
@limiter.limit(settings.rate_limit_delete)
async def delete_url(
    request: Request,
    short_code: str,
    session: AsyncSession = Depends(get_async_session),
    redis: aioredis.Redis = Depends(get_redis_client),
):
    url_repo = URLRepository(session)
    cache_repo = CacheRepository(redis)
    service = URLService(url_repo, cache_repo)
    await service.delete_url(short_code)
    # FastAPI automatically returns 204 when no content returned