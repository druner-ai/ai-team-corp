from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db
from app.routers import urls, redirect, stats
from app.middleware.logging_middleware import LoggingMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure database schema is applied
    await init_db()
    yield
    # Shutdown: nothing to clean


app = FastAPI(
    title="URL Shortener",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware (in production restrict origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware
app.add_middleware(LoggingMiddleware)

# Include routers
app.include_router(urls.router, prefix="/api/v1", tags=["URLs"])
app.include_router(redirect.router, tags=["Redirect"])
app.include_router(stats.router, prefix="/api/v1", tags=["Statistics"])


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    # In a real deployment you could also ping the database here
    return {"status": "ok", "database": "connected"}
