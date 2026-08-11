"""
URL Shortener Service - FastAPI Application

Основной модуль приложения. Инициализирует FastAPI, подключает роутеры,
управляет жизненным циклом БД.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from app.database import init_db
from app.routers import redirect, stats, urls


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Управление жизненным циклом приложения.
    При старте инициализирует БД (создаёт таблицы, если их нет).
    """
    await init_db()
    yield


app = FastAPI(
    title="URL Shortener",
    description="Сервис для сокращения URL с отслеживанием статистики переходов",
    version="1.0.0",
    lifespan=lifespan,
)

# Подключаем роутеры
app.include_router(urls.router)
app.include_router(redirect.router)
app.include_router(stats.router)


@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    """Проверка работоспособности сервиса."""
    return {"status": "ok"}
