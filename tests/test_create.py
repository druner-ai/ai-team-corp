# tests/test_create.py
import pytest


def test_create_url_success(client):
    """Успешное создание короткой ссылки."""
    response = client.post("/shorten", json={"url": "https://example.com"})
    assert response.status_code == 201
    data = response.json()
    assert "short_code" in data
    assert data["original_url"] == "https://example.com"


def test_create_url_with_custom_code(client):
    """Создание ссылки с кастомным кодом."""
    response = client.post(
        "/shorten",
        json={"url": "https://example.com", "custom_code": "test123"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["short_code"] == "test123"


def test_create_url_duplicate_custom_code(client):
    """Попытка дублирования кастомного кода."""
    client.post("/shorten", json={"url": "https://example.com", "custom_code": "test123"})
    response = client.post(
        "/shorten",
        json={"url": "https://other.com", "custom_code": "test123"},
    )
    assert response.status_code == 409
