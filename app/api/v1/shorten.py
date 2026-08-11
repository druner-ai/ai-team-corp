from fastapi import APIRouter, Depends, HTTPException, status
import aiosqlite

from app.api.deps import get_db
from app.models.shorten import ShortenRequest, ShortenResponse
from app.services.url_service import create_short_url

router = APIRouter()


@router.post(
    "/shorten",
    response_model=ShortenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def shorten_url(
    request: ShortenRequest,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Create a short URL from a long URL."""
    try:
        result = await create_short_url(db, str(request.url))
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate unique short code",
        )
