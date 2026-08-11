"""
Health check endpoint router.

Provides a simple endpoint for monitoring application availability.
"""
import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """
    Health check endpoint.

    Returns a simple status indicator to confirm the API is running.

    Returns:
        dict with status "ok".
    """
    logger.debug("Health check requested")
    return {"status": "ok"}