"""
Router for GET /health endpoint.
"""

from fastapi import APIRouter

from app.models.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=200,
    summary="Health check",
    description="Returns the service health status.",
)
async def health_check() -> HealthResponse:
    """
    Simple health check endpoint.

    Returns:
        HealthResponse indicating the service is running.
    """
    return HealthResponse(status="ok")
