"""
API endpoint for redirecting short codes to original URLs.

GET /{short_code}
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse

from src.repositories.database import get_db
from src.services.url_service import URLService

router = APIRouter()


@router.get(
    "/{short_code}",
    response_class=RedirectResponse,
    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    summary="Redirect to original URL",
    description="Redirects to the original URL associated with the given short code.",
)
async def redirect_to_original(
    short_code: str,
    db=Depends(get_db),
) -> RedirectResponse:
    """
    Redirect to the original URL for the given short code.

    Args:
        short_code: The short code to look up.
        db: Database connection (injected via dependency).

    Returns:
        A 307 Temporary Redirect to the original URL.

    Raises:
        HTTPException: 404 if the short code is not found.
    """
    service = URLService(db)
    original_url = await service.redirect(short_code)
    if original_url is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Short code not found",
        )
    return RedirectResponse(url=original_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
