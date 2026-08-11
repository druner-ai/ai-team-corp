import aiosqlite
from typing import Optional
from app.models import UrlRecord, StatsResponse


async def insert_url(db: aiosqlite.Connection, short_code: str, original_url: str) -> int:
    """Вставляет новую короткую ссылку и возвращает её id."""
    cursor = await db.execute(
        "INSERT INTO urls (short_code, original_url) VALUES (?, ?)",
        (short_code, original_url)
    )
    await db.commit()
    return cursor.lastrowid


async def get_url_by_code(db: aiosqlite.Connection, short_code: str) -> Optional[UrlRecord]:
    """Ищет запись по короткому коду. Возвращает None, если не найдена."""
    cursor = await db.execute(
        "SELECT id, short_code, original_url, created_at, expires_at, is_active FROM urls WHERE short_code = ?",
        (short_code,)
    )
    row = await cursor.fetchone()
    if row is None:
        return None
    return UrlRecord(
        id=row[0],
        short_code=row[1],
        original_url=row[2],
        created_at=row[3],
        expires_at=row[4],
        is_active=row[5]
    )


async def insert_click(db: aiosqlite.Connection, url_id: int,
                       ip: Optional[str] = None,
                       user_agent: Optional[str] = None,
                       referer: Optional[str] = None) -> None:
    """Записывает событие перехода с анонимизированным IP."""
    # Анонимизация IPv4: последний октет заменяется на 0
    if ip:
        parts = ip.split('.')
        if len(parts) == 4:
            ip = '.'.join(parts[:-1]) + '.0'
    await db.execute(
        "INSERT INTO clicks (url_id, ip, user_agent, referer) VALUES (?, ?, ?, ?)",
        (url_id, ip, user_agent, referer)
    )
    await db.commit()


async def get_stats(db: aiosqlite.Connection, short_code: str) -> Optional[StatsResponse]:
    """Возвращает статистику по короткому коду: общее количество переходов и время последнего."""
    url_record = await get_url_by_code(db, short_code)
    if not url_record:
        return None
    cursor = await db.execute(
        "SELECT COUNT(*) FROM clicks WHERE url_id = ?", (url_record.id,)
    )
    total = await cursor.fetchone()
    clicks_total = total[0] if total else 0

    cursor = await db.execute(
        "SELECT MAX(clicked_at) FROM clicks WHERE url_id = ?", (url_record.id,)
    )
    last_click = await cursor.fetchone()
    last_click_at = last_click[0] if last_click else None

    return StatsResponse(
        short_code=url_record.short_code,
        original_url=url_record.original_url,
        clicks_total=clicks_total,
        created_at=url_record.created_at,
        last_click_at=last_click_at
    )
