"""
FastAPI application entry point.

Configures:
- Application lifespan (startup/shutdown)
- Exception handlers
- Rate limiting
- CORS
- API routers
- Health check endpoint
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import router as v1_router
from app.config import settings
from app.core.exceptions import (
    URLShortenerException,
    url_shortener_exception_handler,
    generic_exception_handler,
)
from app.core.rate_limiter import create_limiter, setup_rate_limiting
from app.db.redis_client import close_redis_pool, get_redis
from app.db.session import engine

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.dev.ConsoleRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Handles startup and shutdown events:
    - Startup: Initialize connections
    - Shutdown: Close connections gracefully
    """
    logger.info("Starting URL Shortener service...")

    # Initialize Redis pool on startup
    try:
        redis = await get_redis()
        await redis.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.warning(f"Redis not available on startup: {e}")

    yield

    # Cleanup on shutdown
    logger.info("Shutting down URL Shortener service...")
    await close_redis_pool()
    await engine.dispose()
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    app = FastAPI(
        title="URL Shortener",
        description="A high-performance URL shortening microservice",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Set up rate limiting
    limiter = create_limiter()
    setup_rate_limiting(app, limiter)

    # Configure CORS
    if settings.allowed_origins_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.allowed_origins_list,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Register exception handlers
    app.add_exception_handler(URLShortenerException, url_shortener_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    # Include API routers
    app.include_router(v1_router)

    # Health check endpoint
    @app.get(
        "/health",
        summary="Health check",
        description="Check if the service and its dependencies are healthy.",
    )
    async def health_check(request: Request) -> JSONResponse:
        """
        Health check endpoint.

        Checks database and Redis connectivity.
        Returns 200 if all services are healthy, 503 otherwise.
        """
        health_status = {"status": "healthy", "checks": {}}

        # Check database
        try:
            from app.db.session import AsyncSessionLocal
            async with AsyncSessionLocal() as session:
                await session.execute("SELECT 1")
            health_status["checks"]["database"] = "healthy"
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["checks"]["database"] = f"unhealthy: {str(e)}"

        # Check Redis
        try:
            redis = await get_redis()
            await redis.ping()
            health_status["checks"]["redis"] = "healthy"
        except Exception as e:
            health_status["checks"]["redis"] = f"unhealthy: {str(e)}"
            # Redis is not critical - service can work without it
            if health_status["status"] == "healthy":
                health_status["status"] = "degraded"

        status_code = 200 if health_status["status"] == "healthy" else 503
        return JSONResponse(content=health_status, status_code=status_code)

    return app


# Create the application instance
app = create_app()