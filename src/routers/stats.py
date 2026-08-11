"""
Router for statistics endpoint.
"""
from fastapi import APIRouter, Request, HTTPException
from src.models.stats import StatsResponse
from src.services.stats_service import StatsService
from src.database import DatabasePool

router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/stats/{code}", response_model=StatsResponse)
async def get_stats(
    code: str,
    request: Request,
):
    """
    Get click statistics for a short URL.
    """
    pool: DatabasePool = request.app.state.db_pool
    conn = await pool.acquire()
    try:
        service = StatsService(conn)
        stats = await service.get_stats(code)
        if stats is None:
            raise HTTPException(status_code=404, detail="Short URL not found")
        return stats
    except Exception:
        raise
    finally:
        await pool.release(conn)
