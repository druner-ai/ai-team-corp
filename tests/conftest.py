"""Test fixtures and configuration."""

import asyncio
from typing import AsyncGenerator

import aiosqlite
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.db.connection import get_db


@pytest.fixture(scope="function")
async def test_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Create an in-memory SQLite database with schema for each test."""
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA journal_mode=WAL")
    await conn.execute("PRAGMA synchronous=NORMAL")
    await conn.execute("PRAGMA foreign_keys=ON")
    # Apply schema
    with open("app/db/schema.sql") as f:
        schema = f.read()
    await conn.executescript(schema)
    await conn.commit()
    yield conn
    await conn.close()


@pytest.fixture(scope="function")
async def client(test_db: aiosqlite.Connection) -> AsyncGenerator[AsyncClient, None]:
    """Provide an HTTP test client with overridden database dependency."""

    async def override_get_db() -> aiosqlite.Connection:
        return test_db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
