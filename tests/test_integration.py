import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_full_lifecycle(client: AsyncClient):
    # 1. Создание короткой ссылки
    create_response = await client.post("/api/v1/urls", json={"url": "https://example.com"})
    assert create_response.status_code == 201
    data = create_response.json()
    short_code = data["short_code"]
    
    # 2. Редирект по короткой ссылке
    redirect_response = await client.get(f"/api/v1/{short_code}", follow_redirects=False)
    assert redirect_response.status_code == 302
    assert redirect_response.headers["location"] == "https://example.com"
    
    # 3. Просмотр статистики
    stats_response = await client.get(f"/api/v1/urls/{short_code}/stats")
    assert stats_response.status_code == 200
    stats = stats_response.json()
    assert stats["clicks"] == 1
    assert stats["original_url"] == "https://example.com"


@pytest.mark.asyncio
async def test_multiple_redirects_accumulate_clicks(client: AsyncClient):
    # Создаём ссылку
    create_response = await client.post("/api/v1/urls", json={"url": "https://example.com"})
    short_code = create_response.json()["short_code"]
    
    # 5 переходов
    for _ in range(5):
        await client.get(f"/api/v1/{short_code}", follow_redirects=False)
    
    # Проверяем счётчик
    stats_response = await client.get(f"/api/v1/urls/{short_code}/stats")
    assert stats_response.json()["clicks"] == 5


@pytest.mark.asyncio
async def test_custom_code_and_redirect(client: AsyncClient):
    # Создаём с кастомным кодом
    create_response = await client.post("/api/v1/urls", json={
        "url": "https://example.com",
        "custom_code": "test123"
    })
    assert create_response.status_code == 201
    assert create_response.json()["short_code"] == "test123"
    
    # Редирект по кастомному коду
    redirect_response = await client.get("/api/v1/test123", follow_redirects=False)
    assert redirect_response.status_code == 302
