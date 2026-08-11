"""
Pytest fixtures for URL Shortener tests.

Provides test client, in-memory database, and service instances.
"""

import asyncio
import os
import tempfile
from typing import AsyncGenerator, Generator

import aiosqlite
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.config import settings
from app.repositories.database import DatabaseManager
from app.repositories.url_repository import URLRepository
from app.services.url_service import URLService
from app.cache.memory_cache import MemoryCache


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def test_db() -> AsyncGenerator[DatabaseManager, None]:
    """
    Fixture that creates a temporary SQLite database for testing.

    Yields a DatabaseManager connected to an in-memory database.
    """
    db_manager = DatabaseManager(":memory:")
    await db_manager.init()
    yield db_manager


@pytest_asyncio.fixture
async def test_repository(test_db: DatabaseManager) -> URLRepository:
    """Fixture providing a URLRepository with test database."""
    return URLRepository(test_db)


@pytest_asyncio.fixture
async def test_cache() -> MemoryCache:
    """Fixture providing a fresh MemoryCache."""
    return MemoryCache(default_ttl=300)


@pytest_asyncio.fixture
async def test_service(test_repository: URLRepository, test_cache: MemoryCache) -> URLService:
    """Fixture providing a URLService with test repository and cache."""
    return URLService(
        repository=test_repository,
        cache=test_cache,
        base_url="http://test.local",
        short_code_length=6,
    )


@pytest_asyncio.fixture
async def client(test_db: DatabaseManager) -> AsyncGenerator[AsyncClient, None]:
    """
    Fixture providing an HTTP test client.

    Overrides the database dependency to use the test database.
    """
    from app.api import deps

    # Override the database manager dependency
    original_get_db_manager = deps.get_db_manager
    deps.get_db_manager = lambda: test_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Restore original dependency
    deps.get_db_manager = original_get_db_manager
