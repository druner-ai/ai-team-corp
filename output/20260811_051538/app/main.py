"""
FastAPI application entry point.

Creates the FastAPI app instance, registers routers,
configures exception handlers, and sets up startup/shutdown events.
"""
import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import init_db
from app.exceptions.task_exceptions import TaskNotFoundError
from app.routers.health import router as health_router
from app.routers.tasks import router as tasks_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="TODO REST API",
    description="Minimalist REST API for managing a TODO list",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,  # Disable ReDoc for simplicity
)

# Register routers
app.include_router(tasks_router)
app.include_router(health_router)


# Exception handlers
@app.exception_handler(TaskNotFoundError)
async def task_not_found_handler(request: Request, exc: TaskNotFoundError) -> JSONResponse:
    """
    Convert TaskNotFoundError to HTTP 404 response.

    Args:
        request: The incoming request.
        exc: The caught exception.

    Returns:
        JSON response with 404 status and error detail.
    """
    logger.warning("TaskNotFoundError handled: %s", exc)
    return JSONResponse(
        status_code=404,
        content={"detail": "Task not found"},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all handler for unexpected exceptions.

    Args:
        request: The incoming request.
        exc: The caught exception.

    Returns:
        JSON response with 500 status and generic error message.
    """
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Startup event
@app.on_event("startup")
async def startup_event() -> None:
    """
    Initialize database on application startup.

    Enables WAL mode and creates tables if they don't exist.
    """
    logger.info("Starting TODO REST API in %s mode", settings.APP_ENV)
    await init_db()
    logger.info("Application startup complete")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Clean up resources on application shutdown."""
    logger.info("Application shutting down")