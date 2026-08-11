"""
GET /stats/{short_id} endpoint.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.services.url_service import UrlService
from app.schemas.stats import StatsResponse

router = APIRouter()


@router.get("/{short_id}", response_model=StatsResponse)
async def get_stats(
    short_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Return statistics for a shortened URL.
    """
    service = UrlService(db)
    url_obj = await service.get_url(short_id)
    if url_obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL not found")
    if not url_obj.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL not found")
    return StatsResponse.model_validate(url_obj)