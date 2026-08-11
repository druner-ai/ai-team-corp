"""
Test fixtures and configuration.
"""
import pytest
import pytest_asyncio
import aiosqlite
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import init_db, close_db, _db


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    """
    Override the database to use an in-memory SQLite for tests.
    This fixture runs automatically for every test.
    """
    # Replace the global _db with an in-memory connection
    global _db
    _db = await aiosqlite.connect(":memory:")
    _db.row_factory = aiosqlite.Row
    await init_db()
    yield
    await close_db()


@pytest_asyncio.fixture
async def client():
    """
    Async HTTP client for testing the FastAPI app.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
