from fastapi import APIRouter, Depends, status
from app.models import UrlCreateRequest, UrlCreateResponse
from app.services import create_short_url
from app.database import get_db
import aiosqlite
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["shorten"])


@router.post("/shorten", response_model=UrlCreateResponse, status_code=status.HTTP_201_CREATED)
async def shorten_url(request: UrlCreateRequest, db: aiosqlite.Connection = Depends(get_db)):
    """Создаёт короткую ссылку и возвращает её данные."""
    logger.info(f"Shortening URL: {request.url}")
    response = await create_short_url(db, str(request.url))
    return response
