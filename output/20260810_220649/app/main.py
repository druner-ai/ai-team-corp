"""
FastAPI application entry point.
Initializes routers, middleware, and lifespan events.
"""
import contextlib
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api.health import router as health_router
from app.api.v1.router import router as v1_router
from app.config import settings
from app.db.session import close_db, init_db
from app.db.redis_client import close_redis, get_redis
from app.middleware.rate_limit import RateLimitMiddleware


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Lifespan context manager to initialize and shutdown resources.
    """
    logger.info("Starting application...")
    await init_db()
    await get_redis()  # ensure Redis is connected (pool created lazily)
    yield
    logger.info("Shutting down...")
    await close_db()
    await close_redis()


def create_app() -> FastAPI:
    """
    Factory to create and configure the FastAPI application.
    """
    app = FastAPI(
        title="URL Shortener",
        description="A microservice to shorten URLs and track redirects.",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS (optional for development, adjust in production)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rate limiting middleware
    app.add_middleware(
        RateLimitMiddleware,
        redis_url=settings.redis_url,
        limit=settings.rate_limit_per_minute,
    )

    # Include routers
    app.include_router(health_router, tags=["Health"])
    app.include_router(v1_router, prefix="/api/v1", tags=["v1"])

    return app


app = create_app()