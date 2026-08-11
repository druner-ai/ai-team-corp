"""
Application entry point.
Creates FastAPI app, registers routers, and sets up lifespan for DB initialization.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from src.config import settings
from src.database import DatabasePool, init_db
from src.routers import shorten, redirect, stats


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    Initializes the database pool and runs schema setup.
    """
    # Startup: create pool and initialize DB
    app.state.db_pool = DatabasePool(
        db_path=settings.db_path,
        pool_size=settings.db_pool_size,
    )
    await app.state.db_pool.initialize()
    # Run PRAGMA and DDL
    async with app.state.db_pool.acquire() as conn:
        await init_db(conn)
    yield
    # Shutdown: close all connections
    await app.state.db_pool.close()


app = FastAPI(
    title="URL Shortener",
    version="0.1.0",
    lifespan=lifespan,
)

# Register routers
app.include_router(shorten.router)
app.include_router(redirect.router)
app.include_router(stats.router)


@app.get("/health", tags=["health"])
async def healthcheck():
    """Health check endpoint."""
    return {"status": "ok"}
