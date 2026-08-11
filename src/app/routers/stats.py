from fastapi import APIRouter, Depends, HTTPException
import aiosqlite

from ..database import get_db
from ..models import StatsResponse
from ..services.stats_service import get_stats

router = APIRouter()


@router.get("/stats/{code}", response_model=StatsResponse)
async def url_stats(
    code: str,
    conn: aiosqlite.Connection = Depends(get_db),
):
    stats = await get_stats(conn, code)
    if stats is None:
        raise HTTPException(status_code=404, detail="Short URL not found")
    return stats
