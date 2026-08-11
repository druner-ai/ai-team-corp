"""
Test fixtures for the URL shortener service.

Provides an in-memory SQLite database and a configured FastAPI test client.
Each test function gets a fresh database to ensure test isolation.
"""

import asyncio
from typing import AsyncGenerator

import aiosqlite
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.router import api_router
from src.config import settings
from src.repositories.database import get_db

# Override settings for testing
TEST_BASE_URL = "http://test"


@pytest.fixture(scope="function")
async def db_connection() -> AsyncGenerator[aiosqlite.Connection, None]:
    """
    Create a fresh in-memory SQLite database for each test.

    Uses :memory: for speed and isolation. Creates the urls table
    and enables WAL mode.

    Yields:
        An aiosqlite connection to the in-memory database.
    """
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row

    # Enable WAL mode (works even for in-memory DB)
    await conn.execute("PRAGMA journal_mode=WAL")
    await conn.execute("PRAGMA foreign_keys=ON")

    # Create schema
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            short_code TEXT NOT NULL UNIQUE,
            original_url TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            clicks INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    await conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_urls_short_code ON urls(short_code)"
    )
    await conn.commit()

    yield conn
    await conn.close()


@pytest.fixture(scope="function")
async def app(db_connection: aiosqlite.Connection) -> FastAPI:
    """
    Create a FastAPI test application with database dependency override.

    Overrides the get_db dependency to use the test in-memory database.

    Args:
        db_connection: The test database connection fixture.

    Returns:
        A configured FastAPI application instance.
    """
    app = FastAPI()
    app.include_router(api_router)

    async def override_get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
        yield db_connection

    app.dependency_overrides[get_db] = override_get_db
    return app


@pytest.fixture(scope="function")
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """
    Create an async HTTP test client for the FastAPI application.

    Args:
        app: The FastAPI application fixture.

    Yields:
        An httpx AsyncClient configured for ASGI transport.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=TEST_BASE_URL) as ac:
        yield ac
