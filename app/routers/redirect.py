from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.services.url_service import URLService
from app.services.click_service import ClickService

router = APIRouter()


@router.get("/{slug}")
async def redirect_to_url(
    slug: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
    url_svc: URLService = Depends(URLService),
    click_svc: ClickService = Depends(ClickService),
):
    """Перенаправляет на оригинальный URL и записывает клик."""
    url_data = await url_svc.get_url(session, slug)
    if not url_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL not found")

    # Записываем клик
    client_ip = request.client.host if request.client else None
    await click_svc.record_click(session, slug, client_ip)

    return RedirectResponse(url=url_data["original_url"], status_code=status.HTTP_302_FOUND)
