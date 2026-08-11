"""
Pytest fixtures for testing the URL shortener.
"""
import asyncio
import os
import tempfile
from pathlib import Path
from typing import AsyncIterator

import aiosqlite
import pytest
from httpx import AsyncClient, ASGITransport

from src.main import app
from src.database import DatabasePool, init_db


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_db() -> AsyncIterator[aiosqlite.Connection]:
    """
    Create a temporary in-memory SQLite database for testing.
    Yields a connection with WAL mode and schema initialized.
    """
    # Use a temporary file to simulate real DB, but in-memory is fine for tests
    # We'll use a file in a temp directory to test WAL mode properly.
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "test.db")
    conn = await aiosqlite.connect(db_path)
    await conn.execute("PRAGMA journal_mode=WAL")
    await conn.execute("PRAGMA foreign_keys=ON")
    # Run init.sql
    sql_path = Path(__file__).parent.parent / "sql" / "init.sql"
    with open(sql_path, "r", encoding="utf-8") as f:
        ddl = f.read()
    await conn.executescript(ddl)
    await conn.commit()
    yield conn
    await conn.close()
    # Cleanup temp dir
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
async def client(test_db: aiosqlite.Connection) -> AsyncIterator[AsyncClient]:
    """
    Create an HTTPX async client that uses the test database.
    Overrides the app's db_pool dependency to use the test connection.
    """
    # We'll override the lifespan to use our test connection.
    # Instead of using the real pool, we'll create a simple pool-like object that returns the test connection.
    class FakePool:
        def __init__(self, conn):
            self.conn = conn
        async def acquire(self):
            return self.conn
        async def release(self, conn):
            pass  # no-op, we manage the connection externally
        async def close(self):
            pass

    # Store the fake pool in app.state
    app.state.db_pool = FakePool(test_db)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    # Clean up app state
    del app.state.db_pool
