"""
FastAPI application entry point.
Configures middleware, routers, and lifecycle handlers.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.config import settings
from app.db.session import close_engine, engine
from app.db.redis_client import close_redis, get_redis_client
from app.middleware.rate_limit import RateLimitMiddleware
from app.services.cache_service import CacheService
from app.routers import (
    shorten_router,
    redirect_router,
    stats_router,
    delete_router,
    health_router,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events:
    - Startup: Initialize connections
    - Shutdown: Gracefully close all connections
    
    Note:
        Shutdown timeout is configurable via settings.SHUTDOWN_TIMEOUT_SECONDS.
        During shutdown, the service stops accepting new connections and
        waits for existing requests to complete.
    """
    # Startup
    logger.info("Starting URL Shortener service...")
    logger.info(f"Database: {settings.DATABASE_URL}")
    logger.info(f"Redis: {settings.REDIS_URL}")
    
    # Pre-initialize Redis connection
    await get_redis_client()
    logger.info("Redis connection established")
    
    yield
    
    # Shutdown
    logger.info("Shutting down URL Shortener service...")
    
    # Close Redis connections
    await close_redis()
    logger.info("Redis connections closed")
    
    # Close database connections
    await close_engine()
    logger.info("Database connections closed")
    
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        FastAPI: Configured application instance
    """
    app = FastAPI(
        title="URL Shortener",
        description="A high-performance URL shortening microservice",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    
    # Add CORS middleware (allow all origins for API)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Note: RateLimitMiddleware will be added after CacheService is available
    # This is handled in the app startup or through dependency injection
    
    # Register routers
    # Order matters: more specific routes first
    app.include_router(health_router)
    app.include_router(shorten_router)
    app.include_router(stats_router)
    app.include_router(delete_router)
    app.include_router(redirect_router)  # Catch-all for /{id} should be last
    
    return app


# Create application instance
app = create_app()


# Add rate limit middleware
# Note: This is done after app creation because it needs CacheService
@app.on_event("startup")
async def add_rate_limit_middleware():
    """
    Add rate limit middleware after Redis connection is established.
    This is done in startup event because middleware needs CacheService
    which requires Redis client.
    """
    redis_client = await get_redis_client()
    cache_service = CacheService(redis_client)
    
    app.add_middleware(
        RateLimitMiddleware,
        cache_service=cache_service,
        limit=settings.RATE_LIMIT_PER_MINUTE,
    )
    logger.info("Rate limit middleware added")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )