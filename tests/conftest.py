import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
import aiosqlite

from app.main import app
from app.api.deps import get_db

# Override settings for testing
os.environ["DB_PATH"] = ":memory:"
os.environ["BASE_URL"] = "http://testserver"


@pytest_asyncio.fixture
async def test_db():
    """Create an in-memory SQLite database with the application schema."""
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    schema_path = os.path.join(
        os.path.dirname(__file__), "..", "app", "db", "schema.sql"
    )
    with open(schema_path, "r") as f:
        schema_sql = f.read()
    await conn.executescript(schema_sql)
    await conn.commit()
    yield conn
    await conn.close()


@pytest_asyncio.fixture
async def client(test_db):
    """
    Async test client that uses the in-memory database
    by overriding the get_db dependency.
    """
    app.dependency_overrides[get_db] = lambda: test_db
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
