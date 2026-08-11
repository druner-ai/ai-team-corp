# Исправлено: добавлен lifespan для инициализации БД при старте приложения
# Это гарантирует, что таблицы создаются до обработки запросов

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import init_db
from app.routers import urls, redirect, stats


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Инициализация базы данных при старте приложения."""
    await init_db()
    yield


app = FastAPI(title="URL Shortener", lifespan=lifespan)

app.include_router(urls.router, prefix="/api/v1", tags=["urls"])
app.include_router(redirect.router, tags=["redirect"])
app.include_router(stats.router, prefix="/api/v1", tags=["stats"])
