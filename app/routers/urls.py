"""
Роутер для создания коротких ссылок.

POST /shorten — принимает длинный URL, генерирует короткий код,
сохраняет в БД и возвращает короткую ссылку.
"""

import secrets
import string

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException

from app.config import settings
from app.database import get_db
from app.models import URLCreateRequest, URLCreateResponse

router = APIRouter(prefix="/shorten", tags=["URLs"])


def _generate_short_code(length: int = 6) -> str:
    """
    Генерирует криптографически безопасный короткий код.
    Использует буквы (верхний и нижний регистр) и цифры.
    """
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


@router.post("", response_model=URLCreateResponse, status_code=201)
async def create_short_url(
    request: URLCreateRequest,
    db: aiosqlite.Connection = Depends(get_db),
) -> URLCreateResponse:
    """
    Создаёт короткую ссылку для переданного URL.

    - Генерирует уникальный короткий код (6 символов)
    - Сохраняет в БД
    - Возвращает полную короткую ссылку и метаданные
    """
    original_url = str(request.url)

    # Генерируем уникальный код (с повторами при коллизиях)
    for _ in range(10):  # Максимум 10 попыток
        short_code = _generate_short_code(settings.short_code_length)
        try:
            await db.execute(
                "INSERT INTO urls (short_code, original_url) VALUES (?, ?)",
                (short_code, original_url),
            )
            await db.commit()
            break
        except aiosqlite.IntegrityError:
            # Коллизия — пробуем снова
            continue
    else:
        raise HTTPException(
            status_code=500,
            detail="Не удалось сгенерировать уникальный короткий код",
        )

    short_url = f"{settings.base_url}/{short_code}"

    return URLCreateResponse(
        short_url=short_url,
        short_code=short_code,
        original_url=original_url,
    )
