# Fixed: Added routers for health and shorten endpoints. Ensured app includes routers.
# The CI was failing because the FastAPI app did not include the routers, causing 404 for /health and /shorten.
# Also ensured conftest.py properly initializes the test database and overrides the dependency.

from fastapi import FastAPI
from app.routers import health, shorten

app = FastAPI(title="URL Shortener")

app.include_router(health.router)
app.include_router(shorten.router)
