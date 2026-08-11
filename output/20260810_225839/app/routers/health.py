"""
GET /health endpoint.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.redis_client import get_redis_client
from app.schemas.common import HealthResponse
from sqlalchemy import text
import redis.asyncio as aioredis

router = APIRouter(tags=["health"])

@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check",
)
async def health_check(
    session: AsyncSession = Depends(get_async_session),
    redis: aioredis.Redis = Depends(get_redis_client),
) -> HealthResponse:
    """Returns 200 if database and Redis are reachable."""
    db_ok = False
    redis_ok = False
    try:
        await session.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass
    try:
        await redis.ping()
        redis_ok = True
    except Exception:
        pass

    status = "ok" if (db_ok and redis_ok) else "degraded"
    return HealthResponse(
        status=status,
        db_connected=db_ok,
        redis_connected=redis_ok,
    )