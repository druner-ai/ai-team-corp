"""
Тесты для роутера статистики.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_url_stats(client: AsyncClient) -> None:
    """Проверяет получение статистики по существующей ссылке."""
    # Создаём ссылку
    create_response = await client.post(
        "/shorten",
        json={"url": "https://example.com/stats-test"},
    )
    short_code = create_response.json()["short_code"]

    # Получаем статистику
    response = await client.get(f"/stats/{short_code}")
    assert response.status_code == 200
    data = response.json()
    assert data["short_code"] == short_code
    assert data["original_url"] == "https://example.com/stats-test"
    assert data["access_count"] == 0
    assert data["created_at"] is not None


@pytest.mark.asyncio
async def test_get_url_stats_not_found(client: AsyncClient) -> None:
    """Проверяет 404 для несуществующего кода."""
    response = await client.get("/stats/nonexistent")
    assert response.status_code == 404
