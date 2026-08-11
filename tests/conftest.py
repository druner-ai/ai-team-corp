import pytest
import sqlite3
from fastapi.testclient import TestClient
from app.main import app
from app.database.connection import get_db, init_db


@pytest.fixture(autouse=True)
def setup_test_db():
    """Create a fresh in‑memory database before each test."""
    init_db(":memory:")
    yield


@pytest.fixture
def client():
    """Override the get_db dependency to use the in‑memory database."""
    def override_get_db():
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
