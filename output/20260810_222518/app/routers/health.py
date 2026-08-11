"""
Router for GET /health endpoint.
Provides health check for the service.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as redis

from app.schemas.common import HealthResponse
from app.dependencies import get_db_session, get_redis_client

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="Checks service health including database and Redis connectivity."
)
async def health_check(
    db_session: AsyncSession = Depends(get_db_session),
    redis_client: redis.Redis = Depends(get_redis_client),
):
    """
    Perform health check on all dependencies.
    
    Args:
        db_session: Database session
        redis_client: Redis client
        
    Returns:
        HealthResponse: Health status of all components
    """
    # Check database
    db_status = "healthy"
    try:
        await db_session.execute(text("SELECT 1"))
    except Exception:
        db_status = "unhealthy"
    
    # Check Redis
    redis_status = "healthy"
    try:
        await redis_client.ping()
    except Exception:
        redis_status = "unhealthy"
    
    # Overall status
    overall_status = "healthy" if db_status == "healthy" and redis_status == "healthy" else "degraded"
    
    return HealthResponse(
        status=overall_status,
        database=db_status,
        redis=redis_status,
    )