import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_stats_for_existing_link(client: AsyncClient):
    # Создаём URL
    create_response = await client.post("/api/v1/urls", json={"url": "https://example.com"})
    short_code = create_response.json()["short_code"]
    
    # Получаем статистику
    response = await client.get(f"/api/v1/urls/{short_code}/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["short_code"] == short_code
    assert data["original_url"] == "https://example.com"
    assert data["clicks"] == 0
    assert "created_at" in data


@pytest.mark.asyncio
async def test_stats_after_clicks(client: AsyncClient):
    # Создаём URL
    create_response = await client.post("/api/v1/urls", json={"url": "https://example.com"})
    short_code = create_response.json()["short_code"]
    
    # Делаем несколько переходов
    for _ in range(3):
        await client.get(f"/api/v1/{short_code}", follow_redirects=False)
    
    # Проверяем статистику
    response = await client.get(f"/api/v1/urls/{short_code}/stats")
    assert response.status_code == 200
    assert response.json()["clicks"] == 3


@pytest.mark.asyncio
async def test_stats_not_found(client: AsyncClient):
    response = await client.get("/api/v1/urls/nonexistent/stats")
    assert response.status_code == 404
