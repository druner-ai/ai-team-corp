"""
Точка входа FastAPI-приложения.

Создаёт приложение, регистрирует маршруты, добавляет middleware безопасности,
настраивает логирование и обработчики жизненного цикла.
"""
import logging
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.routers import health
from app.config import ENVIRONMENT, LOG_LEVEL, VERSION

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware для добавления заголовков безопасности.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cache-Control"] = "no-store"
        return response


# Создание приложения с условным отключением документации в production
app = FastAPI(
    title="Health Check Service",
    version=VERSION,
    docs_url="/docs" if ENVIRONMENT != "production" else None,
    openapi_url="/openapi.json" if ENVIRONMENT != "production" else None,
)

# Добавление middleware безопасности
app.add_middleware(SecurityHeadersMiddleware)

# Регистрация роутера health check
app.include_router(health.router)


@app.on_event("startup")
async def startup_event() -> None:
    """
    Логирует старт приложения.
    """
    logger.info("Health Check Service starting, version=%s, environment=%s", VERSION, ENVIRONMENT)


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """
    Логирует остановку приложения.
    """
    logger.info("Health Check Service shutting down")


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse | dict:
    """
    Корневой endpoint: редирект на /docs, если документация включена,
    иначе возвращает простое сообщение.
    """
    if app.docs_url:
        return RedirectResponse(url="/docs")
    return {"message": "Health Check Service is running"}
