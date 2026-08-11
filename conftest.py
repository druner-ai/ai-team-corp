"""
Test fixtures and configuration.
"""

import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Override DB_PATH before importing app
os.environ["TEST_DB_PATH"] = str(Path(tempfile.gettempdir()) / "test_urls.db")

# Monkey-patch DB_PATH in connection module
import app.database.connection as db_conn

db_conn.DB_PATH = Path(os.environ["TEST_DB_PATH"])

from app.main import app


@pytest.fixture(autouse=True)
def setup_test_db():
    """Initialize a fresh test database before each test."""
    db_path = Path(os.environ["TEST_DB_PATH"])
    if db_path.exists():
        db_path.unlink()
    db_conn.init_db()
    yield
    # Cleanup after test
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def client():
    return TestClient(app)
