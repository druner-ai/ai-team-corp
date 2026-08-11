"""
API endpoint for redirecting a short URL to its original destination.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db, get_redis
from src.core.exceptions import URLNotFoundError
from src.services.cache_service import CacheService
from src.services.stats_service import StatsService
from src.services.url_service import UrlService

router = APIRouter()


@router.get("/{short_id}", response_class=RedirectResponse, status_code=status.HTTP_302_FOUND)
async def redirect_to_original(
    short_id: str,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> RedirectResponse:
    """
    Redirect to the original URL for the given short ID.

    - **short_id**: The shortened identifier (7 characters, base62).
    """
    cache_service = CacheService(redis)
    url_service = UrlService(db, cache_service)
    try:
        original_url = await url_service.get_original_url(short_id)
    except URLNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL not found")

    # Asynchronously increment click counter
    stats_service = StatsService(redis)
    # Fire and forget; do not block the response
    import asyncio
    asyncio.create_task(stats_service.increment_click(short_id))

    return RedirectResponse(url=original_url, status_code=status.HTTP_302_FOUND)