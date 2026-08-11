"""
API endpoint for deleting (soft) a short URL.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db, get_redis
from src.core.exceptions import URLNotFoundError
from src.services.cache_service import CacheService
from src.services.url_service import UrlService

router = APIRouter()


@router.delete("/{short_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_url(
    short_id: str,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> None:
    """
    Soft-delete a shortened URL.

    - **short_id**: The shortened identifier to delete.
    """
    cache_service = CacheService(redis)
    url_service = UrlService(db, cache_service)
    try:
        await url_service.delete_url(short_id)
        await db.commit()
    except URLNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL not found")