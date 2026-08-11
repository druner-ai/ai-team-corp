from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import RedirectResponse
from app.services import resolve_and_track
from app.database import get_db
import aiosqlite
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{short_code}", status_code=status.HTTP_302_FOUND)
async def redirect_to_original(short_code: str, request: Request, db: aiosqlite.Connection = Depends(get_db)):
    """Редиректит на оригинальный URL, записывая клик."""
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    referer = request.headers.get("referer")
    try:
        original_url = await resolve_and_track(db, short_code, ip, user_agent, referer)
    except Exception as e:
        logger.exception("Error resolving short code %s", short_code)
        raise HTTPException(status_code=500, detail="Internal server error")
    if original_url is None:
        # Уточняем причину ошибки для правильного HTTP-статуса
        from app.repository import get_url_by_code
        url_record = await get_url_by_code(db, short_code)
        if url_record is None:
            raise HTTPException(status_code=404, detail="Short link not found")
        elif not url_record.is_active:
            raise HTTPException(status_code=410, detail="Short link is deactivated")
        elif url_record.expires_at:
            from datetime import datetime
            expires_dt = datetime.fromisoformat(url_record.expires_at)
            if datetime.utcnow() > expires_dt:
                raise HTTPException(status_code=410, detail="Short link expired")
        else:
            raise HTTPException(status_code=404, detail="Short link not found")
    return RedirectResponse(url=original_url, status_code=302)
