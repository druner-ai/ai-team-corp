"""
Main API router that aggregates all versioned routers.
"""

from fastapi import APIRouter

from src.api.v1.health import router as health_router
from src.api.v1.redirect import router as redirect_router
from src.api.v1.shorten import router as shorten_router
from src.api.v1.stats import router as stats_router

api_router = APIRouter()

# Include v1 routers
api_router.include_router(shorten_router, prefix="/api/v1", tags=["shorten"])
api_router.include_router(stats_router, prefix="/api/v1", tags=["stats"])
api_router.include_router(health_router, prefix="/api/v1", tags=["health"])
# Redirect router is mounted at root level for short code resolution
api_router.include_router(redirect_router, tags=["redirect"])
