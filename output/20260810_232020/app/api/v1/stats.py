"""
GET /stats/{short_code} endpoint for URL statistics.
"""

import logging

from fastapi import APIRouter, Depends, Request

from app.api.deps import get_url_service
from app.schemas.stats import StatsResponse
from app.services.url_service import UrlService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/stats/{short_code}",
    response_model=StatsResponse,
    status_code=200,
    summary="Get URL statistics",
    description="Get click statistics and metadata for a short code.",
    responses={
        200: {"description": "Statistics retrieved successfully"},
        404: {"description": "Short code not found"},
    },
)
async def get_url_stats(
    short_code: str,
    request: Request,
    url_service: UrlService = Depends(get_url_service),
) -> StatsResponse:
    """
    Get statistics for a shortened URL.

    Args:
        short_code: The short code.
        request: FastAPI request object.
        url_service: URL service instance.

    Returns:
        StatsResponse with URL metadata and click count.

    Raises:
        URLNotFoundException: If short code not found.
    """
    logger.info(f"Stats request for short_code: {short_code}")

    stats = await url_service.get_stats(short_code)

    return StatsResponse(**stats)