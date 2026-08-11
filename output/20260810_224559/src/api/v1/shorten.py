"""
API endpoint for shortening a URL.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db, get_redis
from src.schemas.url import ShortenRequest, ShortenResponse
from src.services.cache_service import CacheService
from src.services.url_service import UrlService

router = APIRouter()


@router.post("", response_model=ShortenResponse, status_code=status.HTTP_201_CREATED)
async def shorten_url(
    payload: ShortenRequest,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> ShortenResponse:
    """
    Create a short URL from a long original URL.

    - **url**: The original URL to be shortened (must be HTTP/HTTPS, max 2048 characters).
    """
    cache_service = CacheService(redis)
    url_service = UrlService(db, cache_service)
    result = await url_service.create_short_url(str(payload.url))
    return ShortenResponse(**result)