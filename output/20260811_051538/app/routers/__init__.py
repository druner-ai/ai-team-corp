"""
API routers package.

Contains FastAPI routers for all API endpoints.
"""
from app.routers.tasks import router as tasks_router  # noqa: F401
from app.routers.health import router as health_router  # noqa: F401