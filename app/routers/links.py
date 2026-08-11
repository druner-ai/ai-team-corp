from fastapi import APIRouter, Depends, HTTPException, status
import logging

from app.database import DatabaseManager
from app.main import db_manager
from app.models.link import LinkCreateRequest, LinkResponse, StatsResponse
from app.services.url_service import URLService
from app.services.stats_service import StatsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/links", tags=["links"])


async def get_db() -> DatabaseManager:
    """Dependency that provides the database manager."""
    return db_manager


@router.post("", response_model=LinkResponse, status_code=status.HTTP_201_CREATED)
async def create_short_link(
    request: LinkCreateRequest,
    db: DatabaseManager = Depends(get_db),
):
    """
    Create a new short link or return existing one if the URL already exists.
    """
    url_service = URLService(db)
    try:
        result = await url_service.create_short_link(str(request.url))
        return LinkResponse(
            short_code=result["short_code"],
            short_url=result["short_url"],
            original_url=result["original_url"],
            created_at=result["created_at"],
        )
    except RuntimeError as e:
        logger.error(f"Failed to create short link: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error creating short link: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


@router.get("/{short_code}/stats", response_model=StatsResponse)
async def get_link_stats(
    short_code: str,
    db: DatabaseManager = Depends(get_db),
):
    """
    Get statistics for a short link.
    """
    stats_service = StatsService(db)
    try:
        stats = await stats_service.get_stats(short_code)
        if not stats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Short link not found",
            )
        return StatsResponse(
            short_code=stats["short_code"],
            original_url=stats["original_url"],
            clicks=stats["clicks"],
            created_at=stats["created_at"],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving stats for {short_code}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e
