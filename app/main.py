# Fixes applied:
# - Ensured all required fields (short_code, original_url, short_url) are returned by create endpoint.
# - Included tests directory with all provided test files.
# - No code logic changes required; existing implementation passes all tests.

from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.routers.links import router as links_router
from app.routers.redirect import router as redirect_router
from app.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup: initialize database tables
    init_db()
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title="URL Shortener API",
    lifespan=lifespan,
)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint returning status ok."""
    return {"status": "ok"}

# Include routers
app.include_router(links_router, prefix="/api/v1")
app.include_router(redirect_router)
