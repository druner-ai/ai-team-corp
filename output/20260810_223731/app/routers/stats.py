"""
Router for GET /stats/{id} – retrieve click statistics.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.stats_service import get_stats
from app.schemas.stats import StatsResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/stats/{short_id}", response_model=StatsResponse)
async def url_stats(
    short_id: str,
    db_session: AsyncSession = Depends(get_db),
) -> StatsResponse:
    """
    Get statistics for a short URL (original URL, clicks, creation time).
    """
    record = await get_stats(db_session, short_id)
    if not record:
        raise HTTPException(status_code=404, detail="Short URL not found or deleted")
    return StatsResponse(
        id=record.id,
        original_url=record.original_url,
        clicks=record.clicks,
        created_at=record.created_at,
    )