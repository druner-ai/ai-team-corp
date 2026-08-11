"""
URL Shortener - Main Application

ИСПРАВЛЕНИЕ (CI fix):
- Добавлен файл app/database/__init__.py, чтобы 'app.database' стал пакетом.
  Без этого файла Python не распознаёт директорию как пакет, и импорт
  'from app.database.connection import init_db' падает с ошибкой:
  "ModuleNotFoundError: No module named 'app.database.connection'; 'app.database' is not a package"
- Убедился, что conftest.py корректно инициализирует тестовую БД через lifespan.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database.connection import init_db
from app.routers import redirect, stats, urls


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)

app.include_router(urls.router)
app.include_router(redirect.router)
app.include_router(stats.router)
