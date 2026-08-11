"""
Router for GET /{id} endpoint.
Redirects short URLs to original URLs.
"""
from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.url_service import UrlService
from app.dependencies import get_url_service, get_db_session

router = APIRouter(tags=["redirect"])


@router.get(
    "/{short_id}",
    status_code=status.HTTP_302_FOUND,
    responses={
        404: {"description": "Short URL not found"},
        429: {"description": "Rate limit exceeded"},
    },
    summary="Redirect to original URL",
    description="Redirects to the original URL associated with the short ID."
)
async def redirect_to_url(
    short_id: str,
    url_service: UrlService = Depends(get_url_service),
    db_session: AsyncSession = Depends(get_db_session),
):
    """
    Redirect to original URL by short ID.
    
    Args:
        short_id: Short identifier from URL path
        url_service: URL service instance
        db_session: Database session
        
    Returns:
        RedirectResponse: HTTP 302 redirect to original URL
        
    Raises:
        HTTPException: 404 if short ID not found or inactive
    """
    original_url = await url_service.get_original_url(short_id, db_session)
    
    if original_url is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Short URL not found or has been deactivated"
        )
    
    return RedirectResponse(
        url=original_url,
        status_code=status.HTTP_302_FOUND
    )