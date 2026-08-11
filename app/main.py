"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from app.api.routes import router
from app.config import settings
from app.db.connection import close_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifecycle: initialize and close database."""
    await init_db()
    yield
    await close_db()


app = FastAPI(
    title="URL Shortener",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(router)
