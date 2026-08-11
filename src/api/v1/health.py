"""
API endpoint for health checking.

GET /api/v1/health
"""

from fastapi import APIRouter

router = APIRouter()


@router.get(
    "/health",
    summary="Health check",
    description="Returns the health status of the service.",
)
async def health_check() -> dict:
    """
    Health check endpoint.

    Returns:
        A dict with the service status.
    """
    return {"status": "ok"}
