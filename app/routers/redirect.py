from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
import logging

from app.database import DatabaseManager
from app.main import db_manager
from app.services.url_service import URLService
from app.services.stats_service import StatsService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["redirect"])


async def get_db() -> DatabaseManager:
    return db_manager


@router.get("/{short_code}", response_class=RedirectResponse)
async def redirect_to_original(
    short_code: str,
    db: DatabaseManager = Depends(get_db),
):
    """
    Redirect to the original URL and increment the click counter.
    """
    url_service = URLService(db)
    try:
        original_url = await url_service.get_original_url(short_code)
        if not original_url:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Short link not found",
            )

        # Increment clicks
        stats_service = StatsService(db)
        await stats_service.increment_clicks(short_code)

        return RedirectResponse(url=original_url, status_code=status.HTTP_302_FOUND)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing redirect for {short_code}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e
