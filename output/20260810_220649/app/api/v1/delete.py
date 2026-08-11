"""
DELETE /{short_id} endpoint (soft delete).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_redis_client
from app.services.url_service import UrlService
from app.services.cache_service import CacheService

router = APIRouter()


@router.delete("/{short_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_url(
    short_id: str,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis_client),
):
    """
    Soft-delete a shortened URL.
    """
    service = UrlService(db)
    cache = CacheService(redis)
    url_obj = await service.get_url(short_id)
    if url_obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL not found")
    await service.soft_delete_url(short_id)
    # Invalidate cache
    await cache.invalidate_url(short_id)
    return None