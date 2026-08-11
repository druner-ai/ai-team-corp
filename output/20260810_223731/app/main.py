"""
FastAPI application entry point with lifespan, middleware, and routers.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.config import settings
from app.database import engine
from app.redis_client import redis_pool, redis_client
from app.routers import shorten, redirect, stats, delete
from app.middleware.rate_limiter import RateLimiterMiddleware

# Configure structured logging (JSON by default for production)
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "name": "%(name)s", "message": "%(message)s"}',
    datefmt="%Y-%m-%dT%H:%M:%S",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context for startup and graceful shutdown.
    - On startup: validate DB connection, ping Redis.
    - On shutdown: close DB and Redis connection pools.
    """
    # Startup
    logger.info("Starting URL Shortener service")
    # Verify DB connection by trying a trivial operation
    try:
        async with engine.connect() as conn:
            await conn.execute(select(1))
            logger.info("Database connection established")
    except Exception:
        logger.critical("Failed to connect to database", exc_info=True)
        raise
    # Verify Redis connection
    try:
        await redis_client.ping()
        logger.info("Redis connection established")
    except Exception:
        logger.critical("Failed to connect to Redis", exc_info=True)
        raise

    yield

    # Shutdown
    logger.info("Shutting down URL Shortener service")
    await engine.dispose()
    await redis_client.aclose()
    logger.info("Connection pools closed. Goodbye.")


app = FastAPI(
    title="URL Shortener",
    description="Microservice for shortening URLs with analytics and rate limiting.",
    version="1.0.0",
    lifespan=lifespan,
)

# Rate limiter middleware
app.add_middleware(RateLimiterMiddleware)

# Include routers
app.include_router(shorten.router, tags=["shorten"])
app.include_router(redirect.router, tags=["redirect"])
app.include_router(stats.router, tags=["stats"])
app.include_router(delete.router, tags=["delete"])


# Global exception handlers (optional, for better error responses)
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": "Not found"})


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Internal server error", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# Health-check endpoint (not required by spec but useful)
@app.get("/health", include_in_schema=False)
async def health_check():
    return {"status": "ok"}