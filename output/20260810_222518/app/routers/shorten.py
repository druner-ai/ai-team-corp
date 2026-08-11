"""
Router for POST /shorten endpoint.
Creates short URLs from original URLs.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.url import ShortenRequest, ShortenResponse
from app.schemas.common import ErrorResponse
from app.services.url_service import UrlService
from app.dependencies import get_url_service, get_db_session
from app.utils.url_validator import validate_url_safety
from app.config import settings

router = APIRouter(tags=["shorten"])


@router.post(
    "/shorten",
    response_model=ShortenResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid URL"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Create short URL",
    description="Creates a shortened URL from a long URL. Returns the short ID and full short URL."
)
async def create_short_url(
    request: ShortenRequest,
    url_service: UrlService = Depends(get_url_service),
    db_session: AsyncSession = Depends(get_db_session),
):
    """
    Create a new short URL.
    
    Args:
        request: Shorten request with original URL
        url_service: URL service instance
        db_session: Database session
        
    Returns:
        ShortenResponse: Created short URL details
        
    Raises:
        HTTPException: 400 if URL is invalid or unsafe
        HTTPException: 500 if short ID generation fails
    """
    from fastapi import HTTPException
    
    # Additional URL safety validation (SSRF protection)
    is_safe, error_msg = validate_url_safety(str(request.url))
    if not is_safe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg or "URL is not safe to shorten"
        )
    
    try:
        url_mapping = await url_service.create_short_url(
            str(request.url),
            db_session
        )
        
        return ShortenResponse(
            short_id=url_mapping.short_id,
            short_url=f"{settings.BASE_URL}/{url_mapping.short_id}",
            original_url=url_mapping.original_url,
            created_at=url_mapping.created_at,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )