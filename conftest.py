# Fixed: Added database initialization in test fixture (setup_database).
# The CI failed because the 'urls' table was not created in the test database.
# The fixture now overrides DATABASE_URL to a temp file and calls init_db() before each test.
# Also added proper async fixtures for client and database.
import pytest
import os
import tempfile
from httpx import AsyncClient, ASGITransport
from app.main import app
import app.database as db_module

@pytest.fixture(autouse=True)
async def setup_database():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.environ["DATABASE_URL"] = db_path
    old_db_url = db_module.DATABASE_URL
    db_module.DATABASE_URL = db_path
    await db_module.init_db()
    yield
    db_module.DATABASE_URL = old_db_url
    os.unlink(db_path)
    os.close(fd)

@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
