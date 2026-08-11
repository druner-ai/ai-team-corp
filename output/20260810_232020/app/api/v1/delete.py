"""
DELETE /{short_code} endpoint for URL deletion.
"""

import logging

from fastapi import APIRouter, Depends, Request, Response

from app.api.deps import get_url_service
from app.services.url_service import UrlService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.delete(
    "/{short_code}",
    status_code=204,
    summary="Delete a shortened URL",
    description="Soft delete a shortened URL by its short code.",
    responses={
        204: {"description": "URL successfully deleted"},
        404: {"description": "Short code not found"},
        409: {"description": "URL already deleted"},
    },
)
async def delete_url(
    short_code: str,
    request: Request,
    url_service: UrlService = Depends(get_url_service),
) -> Response:
    """
    Soft delete a shortened URL.

    Args:
        short_code: The short code to delete.
        request: FastAPI request object.
        url_service: URL service instance.

    Returns:
        Empty 204 response.

    Raises:
        URLNotFoundException: If short code not found.
        URLAlreadyDeletedException: If already deleted.
    """
    logger.info(f"Delete request for short_code: {short_code}")

    await url_service.delete_url(short_code)

    logger.info(f"Successfully deleted short_code: {short_code}")

    return Response(status_code=204)