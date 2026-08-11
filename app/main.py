"""
FastAPI application entry point.

Sets up the application, registers routers, and manages the database lifecycle.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from app.database import close_db, init_db
from app.routers import health, redirect, shorten, stats

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Initializes the database on startup and closes the connection on shutdown.
    """
    logger.info("Starting up URL Shortener service...")
    await init_db()
    logger.info("Service is ready.")
    yield
    logger.info("Shutting down URL Shortener service...")
    await close_db()
    logger.info("Service stopped.")


app = FastAPI(
    title="URL Shortener",
    description="A simple service to shorten long URLs and track click statistics.",
    version="1.0.0",
    lifespan=lifespan,
)

# Register routers
app.include_router(health.router)
app.include_router(shorten.router)
app.include_router(redirect.router)
app.include_router(stats.router)
