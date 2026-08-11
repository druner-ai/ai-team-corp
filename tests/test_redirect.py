"""
Тесты для роутера редиректа.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_redirect_to_url(client: AsyncClient) -> None:
    """Проверяет редирект по существующей короткой ссылке."""
    # Сначала создаём ссылку
    create_response = await client.post(
        "/shorten",
        json={"url": "https://example.com/target"},
    )
    short_code = create_response.json()["short_code"]

    # Переходим по короткой ссылке
    response = await client.get(f"/{short_code}", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com/target"


@pytest.mark.asyncio
async def test_redirect_not_found(client: AsyncClient) -> None:
    """Проверяет 404 для несуществующего кода."""
    response = await client.get("/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_redirect_increments_counter(client: AsyncClient) -> None:
    """Проверяет, что счётчик переходов увеличивается."""
    # Создаём ссылку
    create_response = await client.post(
        "/shorten",
        json={"url": "https://example.com/counter"},
    )
    short_code = create_response.json()["short_code"]

    # Переходим несколько раз
    for _ in range(3):
        await client.get(f"/{short_code}", follow_redirects=False)

    # Проверяем статистику
    stats_response = await client.get(f"/stats/{short_code}")
    assert stats_response.status_code == 200
    assert stats_response.json()["access_count"] == 3
