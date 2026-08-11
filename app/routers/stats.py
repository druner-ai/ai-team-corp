from fastapi import APIRouter, Depends, HTTPException
from app.database import get_db
from app.config import settings
from app.schemas.stats import StatsResponse, ClickInfo
from app.services.stats_service import StatsService, UrlNotFoundForStats
from app.repositories.url_repository import UrlRepository
from app.repositories.stats_repository import StatsRepository

router = APIRouter()


@router.get("/urls/{slug}/stats", response_model=StatsResponse)
async def get_stats(slug: str, conn=Depends(get_db)):
    """Return click statistics for a given slug."""
    svc = StatsService(UrlRepository(), StatsRepository())
    try:
        stats_data = await svc.get_url_stats(conn, slug, settings.max_recent_clicks)
    except UrlNotFoundForStats as e:
        raise HTTPException(status_code=404, detail=str(e))

    url_data = stats_data["url_data"]
    recent_clicks = [ClickInfo(**click) for click in stats_data["recent_clicks"]]
    return StatsResponse(
        slug=url_data["slug"],
        original_url=url_data["original_url"],
        created_at=url_data["created_at"],
        total_clicks=stats_data["total_clicks"],
        recent_clicks=recent_clicks,
    )
