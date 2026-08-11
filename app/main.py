# app/main.py
# ИСПРАВЛЕНИЯ:
# 1. Добавлен lifespan для инициализации БД при старте приложения
# 2. Добавлен эндпоинт /health для health check (тест test_health_check_returns_ok ожидает 200)
# 3. Добавлен эндпоинт /shorten для создания коротких ссылок (тесты ожидают 201)
# 4. Добавлен эндпоинт /{short_code} для редиректа
# 5. Добавлен эндпоинт /{short_code}/stats для статистики
# 6. Добавлен эндпоинт DELETE /{short_code} для удаления
# 7. Все эндпоинты используют правильные статус-коды согласно тестам

import logging
import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, HttpUrl, field_validator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = os.environ.get("DB_PATH", "urls.db")


def get_db() -> sqlite3.Connection:
    """Получить соединение с БД (синхронное для простоты)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Инициализация таблиц БД."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            short_code TEXT UNIQUE NOT NULL,
            original_url TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            expires_at TEXT,
            clicks INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan для инициализации БД при старте приложения."""
    init_db()
    yield


app = FastAPI(lifespan=lifespan)


class CreateUrlRequest(BaseModel):
    url: HttpUrl
    custom_code: Optional[str] = None
    expires_at: Optional[datetime] = None

    @field_validator("custom_code")
    @classmethod
    def validate_custom_code(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if len(v) < 4 or len(v) > 20:
                raise ValueError("Custom code must be between 4 and 20 characters")
            if not v.isalnum():
                raise ValueError("Custom code must contain only alphanumeric characters")
        return v


class UrlResponse(BaseModel):
    short_code: str
    short_url: str
    original_url: str
    created_at: str
    expires_at: Optional[str] = None


class StatsResponse(BaseModel):
    short_code: str
    original_url: str
    created_at: str
    clicks: int
    expires_at: Optional[str] = None


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/shorten", status_code=201, response_model=UrlResponse)
async def create_short_url(request: Request, body: CreateUrlRequest):
    """Создание короткой ссылки."""
    conn = get_db()
    cursor = conn.cursor()

    # Генерация short_code
    if body.custom_code:
        short_code = body.custom_code
        # Проверка на дубликат
        cursor.execute("SELECT id FROM urls WHERE short_code = ?", (short_code,))
        if cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=409, detail="Custom code already exists")
    else:
        import random
        import string
        while True:
            short_code = "".join(random.choices(string.ascii_letters + string.digits, k=6))
            cursor.execute("SELECT id FROM urls WHERE short_code = ?", (short_code,))
            if not cursor.fetchone():
                break

    created_at = datetime.now(timezone.utc).isoformat()
    expires_at = body.expires_at.isoformat() if body.expires_at else None

    cursor.execute(
        "INSERT INTO urls (short_code, original_url, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (short_code, str(body.url), created_at, expires_at),
    )
    conn.commit()
    conn.close()

    base_url = str(request.base_url).rstrip("/")
    short_url = f"{base_url}/{short_code}"

    return UrlResponse(
        short_code=short_code,
        short_url=short_url,
        original_url=str(body.url),
        created_at=created_at,
        expires_at=expires_at,
    )


@app.get("/{short_code}")
async def redirect_to_url(short_code: str):
    """Редирект по короткой ссылке."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT original_url, expires_at FROM urls WHERE short_code = ?", (short_code,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Short URL not found")

    original_url = row["original_url"]
    expires_at = row["expires_at"]

    # Проверка на истечение срока
    if expires_at:
        expire_dt = datetime.fromisoformat(expires_at)
        if expire_dt < datetime.now(timezone.utc):
            conn.close()
            raise HTTPException(status_code=410, detail="Short URL has expired")

    # Увеличиваем счётчик кликов
    cursor.execute("UPDATE urls SET clicks = clicks + 1 WHERE short_code = ?", (short_code,))
    conn.commit()
    conn.close()

    return RedirectResponse(url=original_url, status_code=302)


@app.get("/{short_code}/stats", response_model=StatsResponse)
async def get_stats(short_code: str):
    """Получение статистики по короткой ссылке."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT short_code, original_url, created_at, clicks, expires_at FROM urls WHERE short_code = ?",
        (short_code,),
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Short URL not found")

    return StatsResponse(
        short_code=row["short_code"],
        original_url=row["original_url"],
        created_at=row["created_at"],
        clicks=row["clicks"],
        expires_at=row["expires_at"],
    )


@app.delete("/{short_code}", status_code=200)
async def delete_short_url(short_code: str):
    """Удаление короткой ссылки."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM urls WHERE short_code = ?", (short_code,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Short URL not found")

    cursor.execute("DELETE FROM urls WHERE short_code = ?", (short_code,))
    conn.commit()
    conn.close()

    return {"short_code": short_code, "deleted": True}
