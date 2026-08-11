# Исправлено: обновлены импорты datetime для использования timezone-aware объектов
# Заменены datetime.utcnow() на datetime.now(datetime.UTC) во всех файлах
# Это исправляет DeprecationWarning и TypeError при сравнении offset-naive и offset-aware datetime

from fastapi import FastAPI
from app.urls.router import router as urls_router

app = FastAPI(title="URL Shortener Service")
app.include_router(urls_router, prefix="/api/v1")
