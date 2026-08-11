import pytest
import sqlite3
from pathlib import Path
from httpx import AsyncClient, ASGITransport

SCHEMA_PATH = Path(__file__).parent.parent / "app" / "database" / "schema.sql"


@pytest.fixture(scope="function")
def db_connection():
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    if SCHEMA_PATH.exists():
        with open(SCHEMA_PATH) as f:
            conn.executescript(f.read())
    else:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS urls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                short_code TEXT NOT NULL UNIQUE,
                original_url TEXT NOT NULL,
                created_at TEXT NOT NULL,
                clicks INTEGER NOT NULL DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_urls_short_code ON urls(short_code);
        """)
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture(scope="function")
async def client(db_connection):
    from app.main import app
    from app.database.connection import get_db

    def override_get_db():
        return db_connection

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
