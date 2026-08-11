"""
URL Shortener Service - FastAPI Application Entry Point.

Initializes the FastAPI application, registers routers, and manages
application lifespan (database initialization, cache setup).
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.redirect import router as redirect_router
from app.api.urls import router as urls_router
from app.api.stats import router as stats_router
from app.config import settings
from app.repositories.database import DatabaseManager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Initializes the database (creates tables, enables WAL mode) on startup
    and closes connections on shutdown.
    """
    logger.info("Starting application...")
    db_manager = DatabaseManager(settings.database_path)
    await db_manager.init()
    logger.info("Database initialized successfully.")
    yield
    logger.info("Shutting down application...")


app = FastAPI(
    title="URL Shortener Service",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS configuration
if settings.allowed_origins:
    origins = [origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Register routers
app.include_router(health_router, tags=["Health"])
app.include_router(redirect_router, tags=["Redirect"])
app.include_router(urls_router, prefix="/api", tags=["URLs"])
app.include_router(stats_router, prefix="/api", tags=["Stats"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
