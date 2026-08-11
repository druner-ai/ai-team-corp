"""
Тесты для основных эндпоинтов.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_shorten_url(client):
    response = client.post("/shorten", json={"url": "https://example.com"})
    assert response.status_code == 200
    data = response.json()
    assert "short_code" in data
    assert "short_url" in data
    assert data["short_url"].endswith(data["short_code"])


@pytest.mark.asyncio
async def test_redirect_and_stats(client):
    # Создаём короткую ссылку
    response = client.post("/shorten", json={"url": "https://example.com"})
    short_code = response.json()["short_code"]

    # Редирект
    redirect_response = client.get(f"/{short_code}", follow_redirects=False)
    assert redirect_response.status_code == 302
    assert redirect_response.headers["location"] == "https://example.com"

    # Статистика
    stats_response = client.get(f"/stats/{short_code}")
    assert stats_response.status_code == 200
    stats = stats_response.json()
    assert stats["click_count"] == 1
    assert stats["original_url"] == "https://example.com"


@pytest.mark.asyncio
async def test_not_found(client):
    response = client.get("/nonexistent")
    assert response.status_code == 404
    response = client.get("/stats/nonexistent")
    assert response.status_code == 404
