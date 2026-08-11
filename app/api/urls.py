"""
API router for URL management endpoints.

POST /api/urls - Create a short URL
GET /api/urls/{short_code} - Get URL information
DELETE /api/urls/{short_code} - Deactivate a short URL
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_url_service
from app.schemas.url import URLCreate, URLResponse, URLInfo
from app.services.url_service import URLService

router = APIRouter()


@router.post("/urls", response_model=URLResponse, status_code=status.HTTP_201_CREATED)
async def create_short_url(
    payload: URLCreate,
    service: URLService = Depends(get_url_service),
) -> URLResponse:
    """
    Create a new short URL.

    Accepts an original URL and optional custom code/expiration.
    Returns the created short URL details.
    """
    try:
        result = await service.create_short_url(
            original_url=str(payload.original_url),
            custom_code=payload.custom_code,
            expires_at=payload.expires_at,
        )
        return URLResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/urls/{short_code}", response_model=URLInfo)
async def get_url_info(
    short_code: str,
    service: URLService = Depends(get_url_service),
) -> URLInfo:
    """
    Get information about a short URL.

    Returns details including click count and last click time.
    """
    result = await service.get_url_info(short_code)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Short link not found")
    return URLInfo(**result)


@router.delete("/urls/{short_code}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_url(
    short_code: str,
    service: URLService = Depends(get_url_service),
) -> None:
    """
    Deactivate a short URL (soft delete).

    Sets is_active to 0, making the link return 410 Gone.
    """
    success = await service.deactivate_url(short_code)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Short link not found")
    return None
