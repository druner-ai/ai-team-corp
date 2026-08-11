"""
Фикстуры для тестов.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client() -> TestClient:
    """
    Создаёт тестовый клиент FastAPI.
    """
    return TestClient(app)
