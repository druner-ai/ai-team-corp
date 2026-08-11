"""
GET /{short_code} endpoint.
"""
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import RedirectResponse
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

@router.get(
    "/{short_code}",
    status_code=status.HTTP_302_FOUND,
    summary="Redirect to original URL",
    description="Redirects using the short code. Returns 404 if not found, 410 if expired.",
    response_class=RedirectResponse,
)
@limiter.limit(settings.rate_limit_redirect)
async def redirect_to_url(
    request: Request,
    short_code: str,
    session: AsyncSession = Depends(get_async_session),
    redis: aioredis.Redis = Depends(get_redis_client),
):
    """
    Redirect to original URL.
    The `request` parameter is needed for rate limiting (slowapi checks client IP).
    """
    url_repo = URLRepository(session)
    cache_repo = CacheRepository(redis)
    service = URLService(url_repo, cache_repo)

    original_url = await service.get_redirect_url(short_code)
    return RedirectResponse(url=original_url, status_code=302)