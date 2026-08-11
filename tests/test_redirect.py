import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_redirect_valid_url(client: AsyncClient):
    # Создаём URL
    create_response = await client.post("/api/v1/urls", json={"url": "https://example.com"})
    short_code = create_response.json()["short_code"]
    
    # Редирект
    response = await client.get(f"/api/v1/{short_code}", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com"


@pytest.mark.asyncio
async def test_redirect_increments_clicks(client: AsyncClient):
    # Создаём URL
    create_response = await client.post("/api/v1/urls", json={"url": "https://example.com"})
    short_code = create_response.json()["short_code"]
    
    # Первый переход
    await client.get(f"/api/v1/{short_code}", follow_redirects=False)
    
    # Проверяем статистику
    stats_response = await client.get(f"/api/v1/urls/{short_code}/stats")
    assert stats_response.status_code == 200
    assert stats_response.json()["clicks"] == 1


@pytest.mark.asyncio
async def test_redirect_not_found(client: AsyncClient):
    response = await client.get("/api/v1/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_redirect_expired_link(client: AsyncClient):
    # Создаём URL с истекающим сроком (0 дней)
    create_response = await client.post("/api/v1/urls", json={
        "url": "https://example.com",
        "expires_in_days": 0
    })
    short_code = create_response.json()["short_code"]
    
    # Пытаемся перейти
    response = await client.get(f"/api/v1/{short_code}", follow_redirects=False)
    assert response.status_code == 404
