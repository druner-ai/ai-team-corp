"""
Router for GET /stats/{id} endpoint.
Returns statistics for a short URL.
"""
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.url import StatsResponse
from app.services.url_service import UrlService
from app.dependencies import get_url_service, get_db_session

router = APIRouter(tags=["stats"])


@router.get(
    "/stats/{short_id}",
    response_model=StatsResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Short URL not found"},
        429: {"description": "Rate limit exceeded"},
    },
    summary="Get URL statistics",
    description="Returns click statistics and metadata for a short URL."
)
async def get_url_stats(
    short_id: str,
    url_service: UrlService = Depends(get_url_service),
    db_session: AsyncSession = Depends(get_db_session),
):
    """
    Get statistics for a short URL.
    
    Args:
        short_id: Short identifier from URL path
        url_service: URL service instance
        db_session: Database session
        
    Returns:
        StatsResponse: URL statistics and metadata
        
    Raises:
        HTTPException: 404 if short ID not found
    """
    stats = await url_service.get_stats(short_id, db_session)
    
    if stats is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Short URL not found"
        )
    
    return StatsResponse(**stats)