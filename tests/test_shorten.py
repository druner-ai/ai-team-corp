import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_short_url_success(client: AsyncClient):
    response = await client.post("/api/v1/shorten", json={"url": "https://example.com/very/long/path"})
    assert response.status_code == 201
    data = response.json()
    assert "short_code" in data
    assert data["short_url"].startswith("http://testserver/")
    assert data["original_url"] == "https://example.com/very/long/path"


@pytest.mark.asyncio
async def test_create_short_url_invalid_url(client: AsyncClient):
    response = await client.post("/api/v1/shorten", json={"url": "not_a_url"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_short_url_missing_url(client: AsyncClient):
    response = await client.post("/api/v1/shorten", json={})
    assert response.status_code == 422
