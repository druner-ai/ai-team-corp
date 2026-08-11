"""
Pytest fixtures for the URL Shortener test suite.

Provides an isolated in-memory SQLite database and a configured test client.
"""

import asyncio
from typing import AsyncGenerator

import aiosqlite
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.database import _connection, get_connection
from app.main import app as fastapi_app
from app.repositories.url_repository import UrlRepository, get_url_repository
from app.services.url_service import UrlService, get_url_service


@pytest.fixture(scope="session")
def event_loop():
    """Create a session-scoped event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """
    Provide an in-memory SQLite database for testing.

    Tables are created fresh for each test function.
    """
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA foreign_keys=ON;")
    await conn.executescript(
        """
        CREATE TABLE urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            original_url TEXT NOT NULL,
            created_at TEXT NOT NULL,
            clicks INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE clicks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url_id INTEGER NOT NULL,
            clicked_at TEXT NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            FOREIGN KEY (url_id) REFERENCES urls(id)
        );
        CREATE INDEX idx_clicks_url_id ON clicks(url_id);
        """
    )
    await conn.commit()

    # Override the global connection for the test
    original_connection = _connection
    # Note: _connection is module-level in database.py; we replace it temporarily
    import app.database as db_module

    db_module._connection = conn

    yield conn

    db_module._connection = original_connection
    await conn.close()


@pytest.fixture
async def client(test_db: aiosqlite.Connection) -> AsyncGenerator[AsyncClient, None]:
    """
    Provide an async HTTP test client configured with the test database.

    Overrides the get_connection dependency to use the in-memory database.
    """

    async def override_get_connection():
        return test_db

    fastapi_app.dependency_overrides[get_connection] = override_get_connection

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    fastapi_app.dependency_overrides.clear()
