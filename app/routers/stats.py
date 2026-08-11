"""
Роутер для получения статистики по короткой ссылке.

GET /stats/{short_code} — возвращает информацию о ссылке и счётчик переходов.
"""

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db
from app.models import URLStatsResponse

router = APIRouter(prefix="/stats", tags=["Statistics"])


@router.get("/{short_code}", response_model=URLStatsResponse)
async def get_url_stats(
    short_code: str,
    db: aiosqlite.Connection = Depends(get_db),
) -> URLStatsResponse:
    """
    Возвращает статистику по указанной короткой ссылке.

    - short_code: код короткой ссылки
    - Возвращает: original_url, created_at, last_accessed_at, access_count
    """
    cursor = await db.execute(
        """
        SELECT short_code, original_url, created_at, last_accessed_at, access_count
        FROM urls
        WHERE short_code = ?
        """,
        (short_code,),
    )
    row = await cursor.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Ссылка не найдена")

    return URLStatsResponse(
        short_code=row[0],
        original_url=row[1],
        created_at=row[2],
        last_accessed_at=row[3],
        access_count=row[4],
    )
