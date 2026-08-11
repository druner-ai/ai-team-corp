from fastapi import APIRouter, Depends, HTTPException, status
import aiosqlite

from app.api.deps import get_db
from app.models.stats import StatsResponse
from app.services.stats_service import get_stats

router = APIRouter()


@router.get("/stats/{code}", response_model=StatsResponse)
async def get_url_stats(
    code: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get statistics for a short URL."""
    stats_data = await get_stats(db, code)
    if stats_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Short URL not found",
        )
    return stats_data
