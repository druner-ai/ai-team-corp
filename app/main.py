# QA Gate report not provided; no fixes applied.
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.config import settings
from app.db.connection import init_db, close_db
from app.api.v1.router import api_router
from app.api.v1.redirect import router as redirect_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan: initialize database on startup,
    close connection on shutdown.
    """
    logger.info("Starting up...")
    conn = await init_db()
    app.state.db = conn
    yield
    logger.info("Shutting down...")
    await close_db(app.state.db)


app = FastAPI(
    title="URL Shortener",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware – restrict origins in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes (prefix /api)
app.include_router(api_router)

# Redirect route at root level (/{code})
app.include_router(redirect_router)


@app.get("/api/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
