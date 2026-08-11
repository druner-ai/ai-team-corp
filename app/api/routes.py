"""API route definitions."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse

from app.schemas.url import ShortenRequest, ShortenResponse, StatsResponse
from app.services.stats_service import StatsService
from app.services.url_service import URLService
from app.db.connection import get_db

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@router.post("/shorten", response_model=ShortenResponse, status_code=status.HTTP_200_OK)
async def shorten_url(
    request: ShortenRequest,
    db=Depends(get_db),
) -> ShortenResponse:
    """Create a short link for the given URL."""
    service = URLService(db)
    try:
        result = await service.create_short_url(str(request.url))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create short link",
        ) from e
    return result


@router.get("/{short_code}")
async def redirect_to_original(
    short_code: str,
    db=Depends(get_db),
) -> RedirectResponse:
    """Redirect to the original URL and increment click counter."""
    service = URLService(db)
    original_url = await service.get_original_url(short_code)
    if original_url is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Short link not found",
        )
    # Increment clicks asynchronously (fire-and-forget is acceptable here,
    # but we await to ensure consistency)
    stats_service = StatsService(db)
    await stats_service.increment_clicks(short_code)
    return RedirectResponse(url=original_url, status_code=status.HTTP_302_FOUND)


@router.get("/stats/{short_code}", response_model=StatsResponse)
async def get_link_stats(
    short_code: str,
    db=Depends(get_db),
) -> StatsResponse:
    """Return statistics for a given short code."""
    stats_service = StatsService(db)
    stats = await stats_service.get_stats(short_code)
    if stats is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Short link not found",
        )
    return stats
