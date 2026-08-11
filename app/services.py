from app.repository import insert_url, get_url_by_code, insert_click, get_stats
from app.shortener import generate_unique_code
from app.config import settings
from app.models import UrlCreateResponse, StatsResponse
import aiosqlite
from datetime import datetime
from typing import Optional


async def create_short_url(db: aiosqlite.Connection, original_url: str) -> UrlCreateResponse:
    """Основная бизнес-логика создания короткой ссылки."""
    short_code = await generate_unique_code(db)
    await insert_url(db, short_code, original_url)
    short_url = f"{settings.base_url}/{short_code}"
    return UrlCreateResponse(
        short_code=short_code,
        short_url=short_url,
        original_url=original_url
    )


async def resolve_and_track(db: aiosqlite.Connection, short_code: str,
                            ip: Optional[str] = None,
                            user_agent: Optional[str] = None,
                            referer: Optional[str] = None) -> Optional[str]:
    """Разрешает короткий код, записывает клик и возвращает исходный URL.
    Возвращает None, если код не найден, неактивен или истёк."""
    url_record = await get_url_by_code(db, short_code)
    if not url_record:
        return None
    if not url_record.is_active:
        return None
    if url_record.expires_at:
        expires_dt = datetime.fromisoformat(url_record.expires_at)
        if datetime.utcnow() > expires_dt:
            return None  # истёк
    await insert_click(db, url_record.id, ip, user_agent, referer)
    return url_record.original_url


async def get_link_stats(db: aiosqlite.Connection, short_code: str) -> Optional[StatsResponse]:
    """Получает статистику по короткой ссылке."""
    return await get_stats(db, short_code)
