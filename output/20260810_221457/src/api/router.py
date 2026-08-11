"""
    Aggregate all routers.
"""
from fastapi import APIRouter
from src.api.shorten import router as shorten_router
from src.api.redirect import router as redirect_router
from src.api.stats import router as stats_router
from src.api.delete import router as delete_router

api_router = APIRouter()
api_router.include_router(shorten_router, tags=["shorten"])
api_router.include_router(redirect_router, tags=["redirect"])
api_router.include_router(stats_router, tags=["stats"])
api_router.include_router(delete_router, tags=["delete"])