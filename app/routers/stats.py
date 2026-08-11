from fastapi import APIRouter, Depends, HTTPException, status
from app.services import get_link_stats
from app.database import get_db
from app.models import StatsResponse
import aiosqlite
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["stats"])


@router.get("/{short_code}/stats", response_model=StatsResponse)
async def get_stats(short_code: str, db: aiosqlite.Connection = Depends(get_db)):
    """Возвращает статистику переходов по короткой ссылке."""
    stats = await get_link_stats(db, short_code)
    if stats is None:
        raise HTTPException(status_code=404, detail="Short link not found")
    return stats
