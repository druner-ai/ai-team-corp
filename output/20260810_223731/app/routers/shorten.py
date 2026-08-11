"""
Router for POST /shorten endpoint.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.url import ShortenRequest, ShortenResponse
from app.services.url_service import create_short_url
from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/shorten", response_model=ShortenResponse, status_code=status.HTTP_201_CREATED)
async def shorten_url(
    payload: ShortenRequest,
    db_session: AsyncSession = Depends(get_db),
) -> ShortenResponse:
    """
    Create a new short URL. Accepts a valid HTTP(S) URL, returns a shortened version.
    """
    original_url = str(payload.url)  # Convert HttpUrl to string
    try:
        record = await create_short_url(db_session, original_url)
    except RuntimeError:
        logger.exception("Failed to create short URL")
        raise HTTPException(status_code=500, detail="Internal error generating short ID")

    short_url = f"{settings.BASE_URL.rstrip('/')}/{record.id}"
    return ShortenResponse(
        id=record.id,
        short_url=short_url,
        original_url=record.original_url,
    )