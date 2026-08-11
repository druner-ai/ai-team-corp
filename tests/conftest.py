import asyncio
import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import DatabaseManager
from app.config import settings


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(name="test_db_path")
def fixture_test_db_path(tmp_path_factory):
    """Return a temporary database file path."""
    return str(tmp_path_factory.mktemp("data") / "test.db")


@pytest_asyncio.fixture(name="test_db_manager")
async def fixture_test_db_manager(test_db_path):
    """Create and initialize a fresh DatabaseManager for testing."""
    manager = DatabaseManager(test_db_path)
    await manager.initialize()
    yield manager
    await manager.close()


@pytest_asyncio.fixture(name="client")
async def fixture_client(test_db_manager: DatabaseManager) -> AsyncGenerator[AsyncClient, None]:
    """
    Create an httpx async client that uses the app with overridden database.
    We override the global db_manager in app.main with the test one.
    """
    # Override the dependency for get_db in routers
    from app.routers.links import get_db as links_get_db
    from app.routers.redirect import get_db as redirect_get_db

    async def override_get_db():
        return test_db_manager

    app.dependency_overrides[links_get_db] = override_get_db
    app.dependency_overrides[redirect_get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    # Clean up overrides
    app.dependency_overrides.clear()
