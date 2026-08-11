from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.services.url_service import URLService
from app.services.click_service import ClickService

router = APIRouter()


class ClickDetail(BaseModel):
    clicked_at: str
    ip_address: str | None


class StatsResponse(BaseModel):
    slug: str
    original_url: str
    created_at: str
    total_clicks: int
    clicks: list[ClickDetail]


@router.get("/stats/{slug}", response_model=StatsResponse)
async def get_stats(
    slug: str,
    session: AsyncSession = Depends(get_session),
    url_svc: URLService = Depends(URLService),
    click_svc: ClickService = Depends(ClickService),
):
    """Возвращает статистику переходов по slug."""
    url_data = await url_svc.get_url(session, slug)
    if not url_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL not found")

    stats = await click_svc.get_stats(session, slug)

    return {
        "slug": slug,
        "original_url": url_data["original_url"],
        "created_at": url_data["created_at"],
        "total_clicks": stats["total_clicks"],
        "clicks": stats["clicks"],
    }
