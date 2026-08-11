from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.config import settings
from app.database import DatabaseManager
from app.routers import links, redirect

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="URL Shortener",
    description="Simple URL shortener service",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database manager instance (singleton in app state)
db_manager = DatabaseManager(settings.database_path)


@app.on_event("startup")
async def startup():
    """Initialize database on application startup."""
    logger.info("Starting application...")
    await db_manager.initialize()
    logger.info("Application started successfully")


@app.on_event("shutdown")
async def shutdown():
    """Close database connection on shutdown."""
    logger.info("Shutting down application...")
    await db_manager.close()
    logger.info("Application shutdown complete")


# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok"}


# Include routers
app.include_router(links.router)
app.include_router(redirect.router)
