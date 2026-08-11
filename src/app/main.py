from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import settings
from .database import close_db, init_db
from .routers import health, redirect, shorten, stats


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(title="URL Shortener", version="1.0.0", lifespan=lifespan)

app.include_router(health.router, tags=["health"])
app.include_router(shorten.router, prefix="/api/v1", tags=["shorten"])
app.include_router(stats.router, prefix="/api/v1", tags=["stats"])
app.include_router(redirect.router, tags=["redirect"])

# TODO: Add rate limiting middleware
