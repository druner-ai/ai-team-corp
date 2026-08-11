"""Template for FastAPI + SQLite (no ORM) tests.

This template ensures:
- In-memory SQLite database (fast, isolated)
- Tables created before each test, dropped after
- StaticPool for single connection (required for in-memory)
- Compatible with httpx AsyncClient + pytest-asyncio
"""

import pytest
import sqlite3
from pathlib import Path
from httpx import AsyncClient, ASGITransport

# Path to schema file (adjust per project)
SCHEMA_PATH = Path(__file__).parent.parent / "sql" / "init.sql"


@pytest.fixture(scope="function")
def db_connection():
    """Create in-memory SQLite database with schema applied."""
    # :memory: = in-memory database (fast, isolated, auto-cleaned)
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row  # dict-like access

    # Apply schema
    if SCHEMA_PATH.exists():
        with open(SCHEMA_PATH) as f:
            conn.executescript(f.read())
    else:
        # Fallback: create tables inline (adjust per project)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS urls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                short_code TEXT UNIQUE NOT NULL,
                original_url TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                visits INTEGER DEFAULT 0
            );
        """)
    conn.commit()

    yield conn

    conn.close()


@pytest.fixture(scope="function")
async def client(db_connection, monkeypatch):
    """FastAPI test client with mocked database connection."""
    from app.main import app  # adjust import per project

    # Override database dependency
    def override_get_db():
        return db_connection

    # Try common dependency names
    from app.database import get_db  # adjust import per project
    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
