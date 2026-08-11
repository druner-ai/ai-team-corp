"""
Health check endpoint.

GET /health - Returns service health status.
"""

from fastapi import APIRouter, Depends

from app.api.deps import get_db_manager
from app.repositories.database import DatabaseManager

router = APIRouter()


@router.get("/health")
async def health_check(
    db_manager: DatabaseManager = Depends(get_db_manager),
) -> dict:
    """
    Health check endpoint.

    Verifies database connectivity and returns service status.
    """
    db_status = "disconnected"
    try:
        async with db_manager.get_connection() as conn:
            await conn.execute("SELECT 1")
            db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return {
        "status": "ok" if db_status == "connected" else "degraded",
        "database": db_status,
    }
