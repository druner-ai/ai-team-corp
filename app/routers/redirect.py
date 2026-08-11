"""
Router for GET /{code} redirect endpoint.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from app.services.url_service import UrlService, get_url_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["redirect"])


@router.get(
    "/{code}",
    response_class=RedirectResponse,
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    summary="Redirect to original URL",
    description="Looks up the short code and redirects to the original URL. Increments click counter.",
)
async def redirect_to_original(
    code: str,
    request: Request,
    service: UrlService = Depends(get_url_service),
) -> RedirectResponse:
    """
    Redirect to the original URL associated with the given short code.

    Args:
        code: The short code from the URL path.
        request: The incoming request (used to extract client metadata).
        service: Injected URL service.

    Returns:
        RedirectResponse with 307 status and Location header.

    Raises:
        HTTPException 404: If the code is not found.
    """
    original_url = await service.get_original_url_and_increment_clicks(
        code=code,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    if original_url is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Short URL not found.",
        )

    return RedirectResponse(url=original_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
