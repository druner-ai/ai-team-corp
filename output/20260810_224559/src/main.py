"""
FastAPI application entry point.

Initializes middleware, routers, background tasks, and provides a health endpoint.
"""
import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.core.database import engine
from src.core.redis_client import redis_client
from src.middleware.logging import RequestLoggingMiddleware
from src.middleware.rate_limit import RateLimitMiddleware
from src.api.v1.router import router as v1_router
from src.services.stats_flusher import StatsFlusher

# Configure structlog
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer() if settings.app_env == "development" else structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

flusher: StatsFlusher | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan: startup and shutdown events.

    - Start StatsFlusher background task.
    - Ensure database connection pool is ready.
    - Gracefully close connections.
    """
    global flusher
    logger.info("Application startup")
    # Start the background flusher
    flusher = StatsFlusher(redis_client)
    await flusher.start()

    yield

    logger.info("Application shutting down")
    if flusher:
        await flusher.stop()
    await redis_client.close()
    await engine.dispose()
    logger.info("Shutdown complete")


app = FastAPI(
    title="URL Shortener",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(",") if settings.cors_origins != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom middleware (order matters: logging then rate limit)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimitMiddleware, redis_client=redis_client)

# API routers
app.include_router(v1_router)


@app.get("/health", response_model=dict, status_code=status.HTTP_200_OK)
async def health_check() -> dict:
    """
    Health check endpoint.

    Verifies connectivity to PostgreSQL and Redis.
    """
    db_status = "up"
    redis_status = "up"

    # Check database
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        db_status = "down"

    # Check Redis
    try:
        await redis_client.ping()
    except Exception:
        redis_status = "down"

    overall = "ok" if (db_status == "up" and redis_status == "up") else "degraded"

    return {
        "status": overall,
        "database": db_status,
        "redis": redis_status,
    }