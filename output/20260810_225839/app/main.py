"""
FastAPI application entry point.
Sets up middleware, routers, and lifespan events.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.database import engine, Base
from app.exceptions.handlers import register_exception_handlers
from app.middleware.rate_limiter import limiter
from app.routers import health, redirect, shorten, stats, delete


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown events."""
    # Startup: nothing to do (DB tables handled by Alembic)
    yield
    # Shutdown: close database connections
    await engine.dispose()


app = FastAPI(
    title="URL Shortener",
    description="Microservice for shortening URLs with caching and statistics",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS: allow GET for redirects (open by default, can be restricted)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Rate limiter middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Register custom exception handlers
register_exception_handlers(app)

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(shorten.router, prefix="/shorten", tags=["shorten"])
app.include_router(redirect.router, tags=["redirect"])
app.include_router(stats.router, prefix="/stats", tags=["stats"])
app.include_router(delete.router, tags=["delete"])