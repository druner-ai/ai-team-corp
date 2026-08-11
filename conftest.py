import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db, init_db
import sqlite3

# Use in-memory database for tests
TEST_DB = ":memory:"

def override_get_db():
    conn = sqlite3.connect(TEST_DB)
    conn.row_factory = sqlite3.Row
    return conn

@pytest.fixture(autouse=True)
def setup_db():
    # Override the dependency
    app.dependency_overrides[get_db] = override_get_db
    # Initialize the test database
    conn = sqlite3.connect(TEST_DB)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS urls (
            short_code TEXT PRIMARY KEY,
            original_url TEXT NOT NULL,
            clicks INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    yield
    # Clean up after test
    conn.execute("DELETE FROM urls")
    conn.commit()
    conn.close()

@pytest.fixture
def client():
    return TestClient(app)
