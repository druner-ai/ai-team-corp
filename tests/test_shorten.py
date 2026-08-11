# tests/test_shorten.py
import pytest


def test_create_short_url(client):
    """Создание короткой ссылки без custom_code."""
    response = client.post("/shorten", json={"url": "https://example.com"})
    assert response.status_code == 201
    data = response.json()
    assert "short_code" in data
    assert "short_url" in data
    assert data["original_url"] == "https://example.com"
    assert len(data["short_code"]) == 6


def test_create_with_custom_code(client):
    """Создание короткой ссылки с custom_code."""
    response = client.post(
        "/shorten",
        json={"url": "https://example.com", "custom_code": "mycode"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["short_code"] == "mycode"
    assert "mycode" in data["short_url"]


def test_create_duplicate_custom_code(client):
    """Попытка создать ссылку с уже существующим custom_code."""
    client.post("/shorten", json={"url": "https://example.com", "custom_code": "mycode"})
    response = client.post(
        "/shorten",
        json={"url": "https://other.com", "custom_code": "mycode"},
    )
    assert response.status_code == 409


def test_create_invalid_url_scheme(client):
    """Попытка создать ссылку с невалидным URL."""
    response = client.post("/shorten", json={"url": "not-a-url"})
    assert response.status_code == 422


def test_create_missing_url_field(client):
    """Попытка создать ссылку без поля url."""
    response = client.post("/shorten", json={})
    assert response.status_code == 422


def test_create_with_expires_at(client):
    """Создание ссылки с expires_at."""
    response = client.post(
        "/shorten",
        json={
            "url": "https://example.com",
            "expires_at": "2026-12-31T23:59:59Z",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["expires_at"] == "2026-12-31T23:59:59+00:00"


def test_create_custom_code_invalid_format(client):
    """Попытка создать ссылку с невалидным custom_code (слишком короткий)."""
    response = client.post(
        "/shorten",
        json={"url": "https://example.com", "custom_code": "ab"},
    )
    assert response.status_code == 422


def test_delete_existing_short_code(client):
    """Удаление существующей короткой ссылки."""
    create_resp = client.post("/shorten", json={"url": "https://example.com"})
    short_code = create_resp.json()["short_code"]

    delete_resp = client.delete(f"/{short_code}")
    assert delete_resp.status_code == 200
    data = delete_resp.json()
    assert data["short_code"] == short_code
    assert data["deleted"] is True

    # Проверяем, что ссылка действительно удалена
    get_resp = client.get(f"/{short_code}")
    assert get_resp.status_code == 404
