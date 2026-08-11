from fastapi import APIRouter, Request, Depends, HTTPException, BackgroundTasks
from fastapi.responses import RedirectResponse
from app.database import get_db
from app.services.url_service import UrlService
from app.services.stats_service import StatsService
from app.repositories.url_repository import UrlRepository
from app.repositories.stats_repository import StatsRepository

router = APIRouter(prefix="/r", tags=["Redirect"])


@router.get("/{slug}")
async def redirect(
    slug: str,
    request: Request,
    background_tasks: BackgroundTasks,
    conn=Depends(get_db),
):
    """Look up a slug and issue a 302 redirect. Records the click asynchronously."""
    url_svc = UrlService(UrlRepository())
    url_data = await url_svc.get_active_url(conn, slug)
    if url_data is None:
        raise HTTPException(status_code=404, detail="URL not found")

    target_url = url_data["original_url"]

    # Extract client information for statistics
    ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
    if not ip and request.client:
        ip = request.client.host
    user_agent = request.headers.get("User-Agent")
    referer = request.headers.get("Referer")

    stats_svc = StatsService(UrlRepository(), StatsRepository())
    background_tasks.add_task(
        stats_svc.record_click_background, slug, ip, user_agent, referer
    )

    return RedirectResponse(url=target_url, status_code=302)
