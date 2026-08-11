"""
GET /{short_id} redirect endpoint.
"""
from fastapi import APIRouter, Depends, HTTPException, Response, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_redis_client
from app.services.url_service import UrlService
from app.services.cache_service import CacheService

router = APIRouter()


@router.get("/{short_id}")
async def redirect_to_original(
    short_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis_client),
):
    """
    Redirect to the original URL using the short ID.
    Checks cache first, then DB. Increments click counter and updates DB in background.
    """
    service = UrlService(db)
    cache = CacheService(redis)

    # Try cache
    cached_url = await cache.get_cached_url(short_id)
    if cached_url:
        # Increment counter in background
        background_tasks.add_task(service.increment_click_count, short_id)
        return Response(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": cached_url},
        )

    # Fetch from DB
    url_obj = await service.get_url(short_id)
    if url_obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL not found")
    if not url_obj.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL not found")
    if url_obj.expires_at is not None and url_obj.expires_at < service._now():
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="URL expired")

    # Store in cache for next time
    await cache.set_cached_url(short_id, url_obj.original_url)

    # Increment counter (background)
    background_tasks.add_task(service.increment_click_count, short_id)

    return Response(
        status_code=status.HTTP_302_FOUND,
        headers={"Location": url_obj.original_url},
    )