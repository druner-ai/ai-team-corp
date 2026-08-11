import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_stats_returns_click_data(client: AsyncClient):
    """Тест получения статистики с данными о кликах."""
    # Создаём ссылку
    create_resp = await client.post(
        "/api/v1/urls",
        json={"original_url": "https://example.com"},
    )
    slug = create_resp.json()["slug"]

    # Делаем несколько переходов
    await client.get(f"/{slug}", follow_redirects=False)
    await client.get(f"/{slug}", follow_redirects=False)

    # Получаем статистику
    response = await client.get(f"/api/v1/stats/{slug}")
    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == slug
    assert data["original_url"] == "https://example.com"
    assert data["total_clicks"] == 2
    assert len(data["clicks"]) == 2
    assert "clicked_at" in data["clicks"][0]


@pytest.mark.asyncio
async def test_stats_not_found(client: AsyncClient):
    """Тест 404 при запросе статистики несуществующей ссылки."""
    response = await client.get("/api/v1/stats/nonexistent")
    assert response.status_code == 404
