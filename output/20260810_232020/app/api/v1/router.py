"""
Main v1 API router that includes all endpoint routers.
"""

from fastapi import APIRouter

from app.api.v1.shorten import router as shorten_router
from app.api.v1.redirect import router as redirect_router
from app.api.v1.stats import router as stats_router
from app.api.v1.delete import router as delete_router

# Create main v1 router
router = APIRouter(prefix="/v1")

# Include sub-routers
router.include_router(shorten_router, tags=["Shorten"])
router.include_router(redirect_router, tags=["Redirect"])
router.include_router(stats_router, tags=["Stats"])
router.include_router(delete_router, tags=["Delete"])