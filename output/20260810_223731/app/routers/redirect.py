"""
Router for GET /{id} – redirect to the original URL.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from fastapi.responses import RedirectResponse

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, async_session_factory
from app.services.url_service import get_original_url
from app.services.stats_service import increment_clicks
from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


async def _increment_clicks_bg(short_id: str):
    """Background task: create a fresh DB session and increment click counter."""
    async with async_session_factory() as session:
        await increment_clicks(session, short_id)


@router.get("/{short_id}", status_code=status.HTTP_302_FOUND)
async def redirect_to_original(
    short_id: str,
    background_tasks: BackgroundTasks,
    db_session: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """
    Redirect to the original long URL. Increments the click counter
    as a background task using a dedicated session.
    """
    record = await get_original_url(db_session, short_id)
    if not record or record.deleted:
        raise HTTPException(status_code=404, detail="Short URL not found")

    # Schedule with a new session (not the request-scoped one)
    background_tasks.add_task(_increment_clicks_bg, short_id)

    logger.info("Redirecting %s -> %s", short_id, record.original_url[:80])
    return RedirectResponse(url=record.original_url, status_code=302)