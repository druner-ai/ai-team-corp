import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_shorten_url(client: AsyncClient):
    response = await client.post("/shorten", json={"url": "https://example.com"})
    assert response.status_code == 200
    data = response.json()
    assert "short_code" in data
    assert data["original_url"] == "https://example.com"
    assert data["short_url"].startswith("http://test/")


@pytest.mark.asyncio
async def test_redirect(client: AsyncClient):
    # Сначала создаём короткую ссылку
    resp = await client.post("/shorten", json={"url": "https://example.org"})
    short_code = resp.json()["short_code"]

    # Переходим по ней
    redirect_resp = await client.get(f"/{short_code}", follow_redirects=False)
    assert redirect_resp.status_code == 302
    assert redirect_resp.headers["location"] == "https://example.org"


@pytest.mark.asyncio
async def test_stats(client: AsyncClient):
    # Создаём ссылку
    resp = await client.post("/shorten", json={"url": "https://example.net"})
    short_code = resp.json()["short_code"]

    # Делаем переход
    await client.get(f"/{short_code}", follow_redirects=False)

    # Запрашиваем статистику
    stats_resp = await client.get(f"/stats/{short_code}")
    assert stats_resp.status_code == 200
    data = stats_resp.json()
    assert data["click_count"] == 1
    assert data["original_url"] == "https://example.net"
    assert len(data["top_referers"]) >= 0
    assert len(data["top_user_agents"]) >= 0


@pytest.mark.asyncio
async def test_not_found(client: AsyncClient):
    response = await client.get("/nonexistent")
    assert response.status_code == 404
    assert response.json()["detail"] == "Short URL not found"
