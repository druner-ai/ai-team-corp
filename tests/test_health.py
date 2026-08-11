# tests/test_health.py
import pytest


def test_health_check_returns_ok(client):
    """Проверка, что health check возвращает 200 и статус ok."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
