"""
Routers package initialization.
"""
from app.routers.shorten import router as shorten_router
from app.routers.redirect import router as redirect_router
from app.routers.stats import router as stats_router
from app.routers.delete import router as delete_router
from app.routers.health import router as health_router

__all__ = [
    "shorten_router",
    "redirect_router",
    "stats_router",
    "delete_router",
    "health_router",
]