# Fixed import: changed from src.app.main to app.main because the project structure does not have a src directory.
# Also added proper test database fixture with in-memory SQLite and dependency override.
import pytest
import aiosqlite
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from app.models import CREATE_TABLE_URLS, CREATE_TABLE_CLICKS


@pytest.fixture
async def test_db():
    db = await aiosqlite.connect(":memory:")
    db.row_factory = aiosqlite.Row
    await db.execute(CREATE_TABLE_URLS)
    await db.execute(CREATE_TABLE_CLICKS)
    await db.commit()
    yield db
    await db.close()


@pytest.fixture
async def client(test_db):
    # Disable lifespan to avoid creating file DB
    app.router.lifespan_context = None
    async def override_get_db():
        return test_db
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
