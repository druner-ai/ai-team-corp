"""
API router for URL statistics.

GET /api/urls/{short_code}/stats - Get click statistics for a short URL.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_url_service
from app.schemas.stats import StatsResponse
from app.services.url_service import URLService

router = APIRouter()


@router.get("/urls/{short_code}/stats", response_model=StatsResponse)
async def get_url_stats(
    short_code: str,
    limit: int = Query(default=20, ge=1, le=100, description="Number of recent clicks to return"),
    service: URLService = Depends(get_url_service),
) -> StatsResponse:
    """
    Get click statistics for a short URL.

    Returns total click count, creation date, last click date,
    and a list of recent clicks.
    """
    result = await service.get_url_stats(short_code, limit=limit)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Short link not found")
    return StatsResponse(**result)
