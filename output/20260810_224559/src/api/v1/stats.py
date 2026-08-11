"""
API endpoint for retrieving statistics of a short URL.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db, get_redis
from src.core.exceptions import URLNotFoundError
from src.schemas.url import StatsResponse
from src.services.cache_service import CacheService
from src.services.url_service import UrlService

router = APIRouter()


@router.get("/{short_id}", response_model=StatsResponse)
async def get_stats(
    short_id: str,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> StatsResponse:
    """
    Retrieve click statistics for a given short URL.

    - **short_id**: The shortened identifier (7 characters, base62).
    """
    cache_service = CacheService(redis)
    url_service = UrlService(db, cache_service)
    try:
        stats = await url_service.get_stats(short_id)
    except URLNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL not found")
    return StatsResponse(**stats)