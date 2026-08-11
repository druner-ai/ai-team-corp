from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import settings
from app.database import init_db, close_db
from app.routers import shorten, redirect, stats, health
from app.middleware.rate_limit import RateLimitMiddleware
import logging

logging.basicConfig(level=settings.log_level.upper())
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()


app = FastAPI(title="URL Shortener", version="1.0.0", lifespan=lifespan)

# CORS middleware
origins = [origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()]
if origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Rate limiting middleware
app.add_middleware(RateLimitMiddleware)

# Include routers
app.include_router(shorten.router)
app.include_router(redirect.router)
app.include_router(stats.router)
app.include_router(health.router)
