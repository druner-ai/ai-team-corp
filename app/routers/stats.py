"""
Router for GET /stats/{code} endpoint.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.models.schemas import StatsResponse
from app.services.url_service import UrlService, get_url_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["stats"])


@router.get(
    "/stats/{code}",
    response_model=StatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get URL statistics",
    description="Returns statistics for a given short code: original URL, creation date, and click count.",
)
async def get_stats(
    code: str,
    service: UrlService = Depends(get_url_service),
) -> StatsResponse:
    """
    Retrieve statistics for a short URL.

    Args:
        code: The short code.
        service: Injected URL service.

    Returns:
        StatsResponse with URL metadata and click count.

    Raises:
        HTTPException 404: If the code is not found.
    """
    stats = await service.get_stats(code)
    if stats is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Short URL not found.",
        )
    return StatsResponse(**stats)
