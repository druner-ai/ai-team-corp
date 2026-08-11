import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_shorten_valid_url(client: AsyncClient):
    response = await client.post("/api/shorten", json={"url": "https://example.com"})
    assert response.status_code == 201
    data = response.json()
    assert "code" in data
    assert data["original_url"] == "https://example.com"
    assert data["short_url"].startswith("http://testserver/")


@pytest.mark.asyncio
async def test_shorten_invalid_url(client: AsyncClient):
    response = await client.post("/api/shorten", json={"url": "not-a-url"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_shorten_missing_url(client: AsyncClient):
    response = await client.post("/api/shorten", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_shorten_duplicate_url_creates_new_code(client: AsyncClient):
    response1 = await client.post("/api/shorten", json={"url": "https://example.com"})
    response2 = await client.post("/api/shorten", json={"url": "https://example.com"})
    assert response1.status_code == 201
    assert response2.status_code == 201
    assert response1.json()["code"] != response2.json()["code"]
