"""
POST /shorten endpoint.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.shorten import ShortenRequest, ShortenResponse
from app.services.url_service import UrlService
from app.core.url_validator import validate_url

router = APIRouter()


@router.post("", response_model=ShortenResponse, status_code=status.HTTP_201_CREATED)
async def shorten_url(
    payload: ShortenRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a shortened URL.
    Validates the input URL, generates a short ID, stores it, and returns the short URL.
    """
    # Validate URL (SSRF, scheme, length)
    try:
        validated_url = validate_url(payload.url)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    service = UrlService(db)
    try:
        result = await service.create_short_url(
            original_url=validated_url,
            expires_at=payload.expires_at,
        )
    except RuntimeError as e:
        # Exceeded retry attempts for short_id generation
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate unique short ID. Please try again.",
        )

    return result