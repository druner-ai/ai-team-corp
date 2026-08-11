"""
POST /shorten endpoint for URL shortening.
"""

import logging

from fastapi import APIRouter, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.deps import get_url_service
from app.config import settings
from app.core.exceptions import URLAlreadyExistsException
from app.schemas.shorten import ShortenRequest, ShortenResponse
from app.services.url_service import UrlService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/shorten",
    response_model=ShortenResponse,
    status_code=201,
    summary="Shorten a URL",
    description="Create a shortened URL from a long URL.",
    responses={
        201: {"description": "URL successfully shortened"},
        400: {"description": "Invalid URL provided"},
        409: {"description": "URL already shortened"},
        429: {"description": "Rate limit exceeded"},
    },
)
async def shorten_url(
    request: Request,
    body: ShortenRequest,
    url_service: UrlService = Depends(get_url_service),
) -> ShortenResponse:
    """
    Shorten a long URL.

    Args:
        request: FastAPI request object.
        body: Validated request body with URL.
        url_service: URL service instance.

    Returns:
        ShortenResponse with short code and URLs.

    Raises:
        URLAlreadyExistsException: If URL already has a short code.
    """
    logger.info(f"Shortening URL: {body.url[:50]}...")

    result = await url_service.shorten_url(body.url)

    logger.info(f"Created short code: {result['short_code']}")

    return ShortenResponse(**result)