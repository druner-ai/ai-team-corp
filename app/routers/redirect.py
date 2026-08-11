"""
Роутер для редиректа по короткой ссылке.

GET /{short_code} — ищет код в БД, увеличивает счётчик,
возвращает HTTP 302 редирект на исходный URL.
"""

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse

from app.database import get_db

router = APIRouter(tags=["Redirect"])


@router.get("/{short_code}")
async def redirect_to_url(
    short_code: str,
    db: aiosqlite.Connection = Depends(get_db),
) -> RedirectResponse:
    """
    Обрабатывает переход по короткой ссылке.

    - Ищет short_code в БД
    - Увеличивает счётчик переходов и обновляет last_accessed_at
    - Возвращает 302 редирект на оригинальный URL
    """
    cursor = await db.execute(
        "SELECT original_url FROM urls WHERE short_code = ?",
        (short_code,),
    )
    row = await cursor.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Ссылка не найдена")

    original_url = row[0]

    # Обновляем статистику
    await db.execute(
        """
        UPDATE urls
        SET access_count = access_count + 1,
            last_accessed_at = CURRENT_TIMESTAMP
        WHERE short_code = ?
        """,
        (short_code,),
    )
    await db.commit()

    return RedirectResponse(url=original_url, status_code=302)
