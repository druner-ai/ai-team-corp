"""
API endpoint for retrieving statistics for a short URL.

GET /api/v1/stats/{short_code}
"""

from fastapi import APIRouter, Depends, HTTPException, status

from src.repositories.database import get_db
from src.schemas.url import StatsResponse
from src.services.url_service import URLService

router = APIRouter()


@router.get(
    "/stats/{short_code}",
    response_model=StatsResponse,
    summary="Get statistics for a short URL",
    description="Returns statistics including original URL, click count, and creation date.",
)
async def get_stats(
    short_code: str,
    db=Depends(get_db),
) -> StatsResponse:
    """
    Get statistics for the given short code.

    Args:
        short_code: The short code to look up.
        db: Database connection (injected via dependency).

    Returns:
        StatsResponse with original URL, clicks, and creation date.

    Raises:
        HTTPException: 404 if the short code is not found.
    """
    service = URLService(db)
    stats = await service.get_stats(short_code)
    if stats is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Short code not found",
        )
    return StatsResponse(**stats)
