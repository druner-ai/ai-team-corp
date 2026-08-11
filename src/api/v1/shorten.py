"""
API endpoint for creating short URLs.

POST /api/v1/shorten
"""

from fastapi import APIRouter, Depends, status

from src.repositories.database import get_db
from src.schemas.url import ShortenRequest, ShortenResponse
from src.services.url_service import URLService

router = APIRouter()


@router.post(
    "/shorten",
    response_model=ShortenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a short URL",
    description="Creates a shortened URL from the provided original URL.",
)
async def create_short_url(
    request: ShortenRequest,
    db=Depends(get_db),
) -> ShortenResponse:
    """
    Create a short URL from the provided original URL.

    Args:
        request: The request body containing the original URL.
        db: Database connection (injected via dependency).

    Returns:
        ShortenResponse with the generated short code and URLs.
    """
    service = URLService(db)
    result = await service.create_short_url(str(request.url))
    return ShortenResponse(**result)
