"""Fixtures for FastAPI + SQLite (without ORM) tests.

Key principles:
1. In-memory SQLite (:memory:) - fast, isolated
2. scope="function" - new DB for each test
3. dependency_overrides - substitute FastAPI dependencies
4. pytest-asyncio for async tests
"""

import pytest
import sqlite3
from pathlib import Path
from httpx import AsyncClient, ASGITransport

# Path to the schema relative to tests/
SCHEMA_PATH = Path(__file__).parent.parent / "sql" / "init.sql"


@pytest.fixture(scope="function")
def db_connection():
    """In-memory SQLite with applied schema."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row  # dict-like access

    # Apply schema
    if SCHEMA_PATH.exists():
        with open(SCHEMA_PATH) as f:
            conn.executescript(f.read())
    else:
        # Fallback: inline schema matching architecture
        conn.executescript("""
            PRAGMA foreign_keys = ON;
            CREATE TABLE IF NOT EXISTS urls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                short_code TEXT UNIQUE NOT NULL,
                original_url TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS clicks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url_id INTEGER,
                clicked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ip_address TEXT,
                user_agent TEXT,
                FOREIGN KEY (url_id) REFERENCES urls(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_urls_short_code ON urls(short_code);
            CREATE INDEX IF NOT EXISTS idx_clicks_url_id ON clicks(url_id);
        """)
    conn.commit()

    yield conn

    conn.close()


@pytest.fixture(scope="function")
async def client(db_connection):
    """FastAPI test client with substituted DB."""
    from app.main import app
    from app.database import get_db

    # Override the dependency
    def override_get_db():
        return db_connection

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    # Clear overrides after test
    app.dependency_overrides.clear()
