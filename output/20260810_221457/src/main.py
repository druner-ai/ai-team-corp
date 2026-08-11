"""
    FastAPI application entry point.

    Sets up all middlewares, routers, and startup/shutdown events.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from sqlalchemy import text

from src.api.router import api_router
from src.config import settings
from src.db.postgres import engine, async_session_maker
from src.db.redis import close_redis_pool
from src.middleware.error_handler import ErrorHandlingMiddleware
from src.middleware.rate_limiter import RateLimiterMiddleware
from src.middleware.request_id import RequestIDMiddleware

logger = logging.getLogger(__name__)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting up")
    async with engine.begin() as conn:
        pass
    yield
    logger.info("Application shutting down")
    await engine.dispose()
    await close_redis_pool()

app = FastAPI(
    title="URL Shortener",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Middleware order (outermost first)
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(RateLimiterMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.include_router(api_router)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/ready")
async def ready():
    try:
        async with async_session_maker() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {"status": "not ready"}, 503