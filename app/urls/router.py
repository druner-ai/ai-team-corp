from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import RedirectResponse
from app.urls.models import URLCreate, URLResponse, URLStats
from app.urls.service import URLService
from app.urls.repository import URLRepository

router = APIRouter()


def get_repository() -> URLRepository:
    return URLRepository()


def get_service(repository: URLRepository = Depends(get_repository)) -> URLService:
    return URLService(repository)


@router.post("/urls", response_model=URLResponse, status_code=201)
async def create_url(url_data: URLCreate, service: URLService = Depends(get_service)):
    try:
        result = await service.create_short_url(
            original_url=str(url_data.url),
            custom_code=url_data.custom_code,
            expires_in_days=url_data.expires_in_days
        )
        return URLResponse(
            short_code=result["short_code"],
            short_url=f"/api/v1/{result['short_code']}",
            original_url=result["original_url"],
            created_at=result["created_at"],
            expires_at=result.get("expires_at")
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/{short_code}")
async def redirect_to_url(short_code: str, service: URLService = Depends(get_service)):
    original_url = await service.get_original_url(short_code)
    if not original_url:
        raise HTTPException(status_code=404, detail="URL not found or expired")
    return RedirectResponse(url=original_url, status_code=302)


@router.get("/urls/{short_code}/stats", response_model=URLStats)
async def get_url_stats(short_code: str, service: URLService = Depends(get_service)):
    stats = await service.get_stats(short_code)
    if not stats:
        raise HTTPException(status_code=404, detail="URL not found")
    return URLStats(
        short_code=stats["short_code"],
        original_url=stats["original_url"],
        created_at=stats["created_at"],
        clicks=stats["clicks"],
        last_accessed=stats.get("last_accessed")
    )
