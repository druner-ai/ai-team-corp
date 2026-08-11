"""
API router for redirect handling.

GET /{short_code} - Redirect to the original URL.
"""

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from app.api.deps import get_url_service
from app.services.url_service import URLService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{short_code}")
async def redirect_to_original(
    short_code: str,
    request: Request,
    service: URLService = Depends(get_url_service),
) -> RedirectResponse:
    """
    Redirect to the original URL based on the short code.

    Records the click asynchronously (fire-and-forget) to minimize latency.
    Returns 301 Moved Permanently on success.
    """
    original_url = await service.get_original_url(short_code)
    if original_url is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Short link not found or expired")

    # Fire-and-forget click recording
    asyncio.create_task(
        service.record_click(
            short_code=short_code,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            referer=request.headers.get("referer"),
        )
    )

    return RedirectResponse(url=original_url, status_code=status.HTTP_301_MOVED_PERMANENTLY)
