"""
POST /shorten endpoint.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_async_session
from app.services.url_service import URLService
from app.repositories.url_repository import URLRepository
from app.repositories.cache_repository import CacheRepository
from app.schemas.url import ShortenRequest, ShortenResponse
from app.middleware.rate_limiter import limiter
from app.config import settings
from app.redis_client import get_redis_client
import redis.asyncio as aioredis

router = APIRouter()

@router.post(
    "/",
    response_model=ShortenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Shorten a URL",
    description="Creates a short URL from a long URL. Optionally set expiration.",
)
@limiter.limit(settings.rate_limit_shorten)
async def create_short_url(
    request_data: ShortenRequest,
    session: AsyncSession = Depends(get_async_session),
    redis: aioredis.Redis = Depends(get_redis_client),
) -> ShortenResponse:
    """Handle POST /shorten."""
    url_repo = URLRepository(session)
    cache_repo = CacheRepository(redis)
    service = URLService(url_repo, cache_repo)

    result = await service.shorten_url(
        original_url=str(request_data.url),
        expires_at=request_data.expires_at,
    )
    return ShortenResponse(**result)