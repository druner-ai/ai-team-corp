import pytest
import tempfile
import os
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import get_db, init_db, DATABASE_URL as ORIGINAL_DB_URL


@pytest.fixture
async def test_db():
    """Create a temporary database for testing."""
    # Use a temporary file to avoid conflicts
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    test_db_url = path

    # Override the database URL used by get_db
    import app.database as db_module
    original_url = db_module.DATABASE_URL
    db_module.DATABASE_URL = test_db_url

    # Initialize the test database
    await init_db()

    yield test_db_url

    # Cleanup
    db_module.DATABASE_URL = original_url
    os.unlink(path)


@pytest.fixture
async def client(test_db):
    """Provide an async HTTP client for testing."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
