import asyncio
import os

import pytest
from httpx import AsyncClient, ASGITransport

# Force in-memory database for all tests
os.environ["DATABASE_URL"] = ":memory:"

# Import app after setting env to ensure the correct DB is used
from app.main import app
from app.database import init_db, close_db, get_connection


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def setup_db():
    """Initialize the test database before each test and clean up after session."""
    await init_db()
    yield
    # Optionally clear data between tests to ensure isolation
    conn = await get_connection()
    await conn.execute("DELETE FROM urls")
    await conn.commit()


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
