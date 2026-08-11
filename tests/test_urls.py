"""
Тесты для роутера создания коротких ссылок.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_short_url(client: AsyncClient) -> None:
    """Проверяет успешное создание короткой ссылки."""
    response = await client.post(
        "/shorten",
        json={"url": "https://example.com/very/long/url"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "short_url" in data
    assert "short_code" in data
    assert data["original_url"] == "https://example.com/very/long/url"
    assert data["short_url"].endswith(data["short_code"])


@pytest.mark.asyncio
async def test_create_short_url_invalid_url(client: AsyncClient) -> None:
    """Проверяет ошибку валидации при невалидном URL."""
    response = await client.post(
        "/shorten",
        json={"url": "not-a-valid-url"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_short_url_duplicate(client: AsyncClient) -> None:
    """Проверяет, что одинаковые URL получают разные короткие коды."""
    url = "https://example.com"
    response1 = await client.post("/shorten", json={"url": url})
    response2 = await client.post("/shorten", json={"url": url})

    assert response1.status_code == 201
    assert response2.status_code == 201
    assert response1.json()["short_code"] != response2.json()["short_code"]
