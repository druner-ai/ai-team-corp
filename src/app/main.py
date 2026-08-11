"""
FastAPI приложение для сервиса сокращения URL.
"""
import hashlib
import string
import random
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl

from .database import (
    get_db,
    init_db,
    create_short_url,
    get_original_url,
    record_click,
    get_stats,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Инициализация БД при старте приложения."""
    await init_db()
    yield


app = FastAPI(title="URL Shortener", lifespan=lifespan)


class ShortenRequest(BaseModel):
    url: HttpUrl


class ShortenResponse(BaseModel):
    short_code: str
    short_url: str


class StatsResponse(BaseModel):
    short_code: str
    original_url: str
    created_at: str
    click_count: int
    last_click: str | None
    top_referers: list[dict]
    top_user_agents: list[dict]


def generate_short_code(length: int = 6) -> str:
    """Генерация случайного короткого кода."""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))


@app.post("/shorten", response_model=ShortenResponse)
async def shorten_url(request: ShortenRequest, db=Depends(get_db)):
    """Создание короткой ссылки."""
    short_code = generate_short_code()
    # Проверка уникальности (простая, без цикла для демонстрации)
    existing = await get_original_url(db, short_code)
    while existing:
        short_code = generate_short_code()
        existing = await get_original_url(db, short_code)

    await create_short_url(db, short_code, str(request.url))
    short_url = f"http://localhost:8000/{short_code}"  # В реальности брать из конфига
    return ShortenResponse(short_code=short_code, short_url=short_url)


@app.get("/{short_code}")
async def redirect_to_original(short_code: str, request: Request, db=Depends(get_db)):
    """Редирект на оригинальный URL с записью клика."""
    original_url = await get_original_url(db, short_code)
    if not original_url:
        raise HTTPException(status_code=404, detail="Short URL not found")

    referer = request.headers.get("referer")
    user_agent = request.headers.get("user-agent")
    await record_click(db, short_code, referer, user_agent)

    return RedirectResponse(url=original_url, status_code=302)


@app.get("/stats/{short_code}", response_model=StatsResponse)
async def get_url_stats(short_code: str, db=Depends(get_db)):
    """Получение статистики по короткой ссылке."""
    stats = await get_stats(db, short_code)
    if not stats:
        raise HTTPException(status_code=404, detail="Short URL not found")
    return StatsResponse(**stats)
