import pytest


@pytest.mark.asyncio
async def test_shorten_url(client):
    response = await client.post("/shorten", json={"url": "https://example.com"})
    assert response.status_code == 201
    data = response.json()
    assert "short_code" in data
    assert "short_url" in data
    assert data["original_url"] == "https://example.com"
    assert data["short_url"].startswith("http://")


@pytest.mark.asyncio
async def test_redirect(client):
    # Сначала создаём короткую ссылку
    response = await client.post("/shorten", json={"url": "https://example.com"})
    assert response.status_code == 201
    short_code = response.json()["short_code"]

    # Переходим по короткой ссылке
    response = await client.get(f"/{short_code}", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com"


@pytest.mark.asyncio
async def test_stats(client):
    # Создаём короткую ссылку
    response = await client.post("/shorten", json={"url": "https://example.com"})
    assert response.status_code == 201
    short_code = response.json()["short_code"]

    # Делаем переход для увеличения счётчика
    await client.get(f"/{short_code}", follow_redirects=False)

    # Получаем статистику
    response = await client.get(f"/stats/{short_code}")
    assert response.status_code == 200
    data = response.json()
    assert data["original_url"] == "https://example.com"
    assert "created_at" in data
    assert data["clicks"] == 1


@pytest.mark.asyncio
async def test_not_found(client):
    response = await client.get("/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_stats_not_found(client):
    response = await client.get("/stats/nonexistent")
    assert response.status_code == 404
