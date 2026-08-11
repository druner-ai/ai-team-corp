from fastapi import APIRouter
from app.api.v1.shorten import router as shorten_router
from app.api.v1.redirect import router as redirect_router
from app.api.v1.stats import router as stats_router
from app.api.v1.delete import router as delete_router

router = APIRouter()
router.include_router(shorten_router, prefix="/shorten", tags=["Shorten"])
router.include_router(redirect_router, tags=["Redirect"])
router.include_router(stats_router, prefix="/stats", tags=["Stats"])
router.include_router(delete_router, tags=["Delete"])