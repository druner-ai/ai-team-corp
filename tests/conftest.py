import pytest
import aiosqlite
import os
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db

TEST_DB = "test_url_shortener.db"


@pytest.fixture(autouse=True)
async def setup_db():
    # Create test database and tables before each test
    async with aiosqlite.connect(TEST_DB) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS urls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT UNIQUE NOT NULL,
                original_url TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS visits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url_id INTEGER NOT NULL,
                visited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address TEXT,
                FOREIGN KEY (url_id) REFERENCES urls (id)
            )
        """)
        await db.commit()
    yield
    # Cleanup after test
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


@pytest.fixture
async def db_connection():
    async with aiosqlite.connect(TEST_DB) as db:
        db.row_factory = aiosqlite.Row
        yield db


@pytest.fixture
async def client(db_connection):
    async def override_get_db():
        yield db_connection

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
