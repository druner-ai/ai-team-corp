"""
Main application entry point.

Creates the FastAPI application, sets up lifespan context for database
initialization and cleanup, and includes the API router.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from src.api.router import api_router
from src.config import settings
from src.repositories.database import close_db, init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager.

    Initializes the database on startup and closes connections on shutdown.
    """
    logger.info("Starting application, initializing database...")
    await init_db(settings.db_path)
    logger.info("Database initialized successfully")
    yield
    logger.info("Shutting down application, closing database...")
    await close_db()
    logger.info("Database connection closed")


app = FastAPI(
    title="URL Shortener Service",
    description="A simple URL shortener service with FastAPI and SQLite",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(api_router)
