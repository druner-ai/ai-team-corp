"""
GET /{short_code} endpoint for URL redirection.
"""

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from app.api.deps import get_url_service
from app.core.exceptions import (
    URLAlreadyDeletedException,
    URLExpiredException,
    URLNotFoundException,
)
from app.services.url_service import UrlService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/{short_code}",
    status_code=307,
    summary="Redirect to original URL",
    description="Redirect to the original URL using the short code.",
    responses={
        307: {"description": "Temporary redirect to original URL"},
        404: {"description": "Short code not found"},
        410: {"description": "URL has expired"},
    },
)
async def redirect_to_url(
    short_code: str,
    request: Request,
    url_service: UrlService = Depends(get_url_service),
) -> RedirectResponse:
    """
    Redirect to the original URL for a given short code.

    Args:
        short_code: The short code from the URL path.
        request: FastAPI request object.
        url_service: URL service instance.

    Returns:
        RedirectResponse with 307 status.

    Raises:
        URLNotFoundException: If short code not found.
        URLAlreadyDeletedException: If URL is deleted.
        URLExpiredException: If URL has expired.
    """
    logger.info(f"Redirect request for short_code: {short_code}")

    original_url = await url_service.get_original_url(short_code)

    logger.info(f"Redirecting {short_code} to {original_url[:50]}...")

    return RedirectResponse(
        url=original_url,
        status_code=307,
    )