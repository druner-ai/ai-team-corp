import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_shorten_valid_url(async_client: AsyncClient):
    resp = await async_client.post("/shorten", json={"url": "https://example.com/long/path"})
    assert resp.status_code == 201
    data = resp.json()
    assert "short_id" in data
    assert data["original_url"] == "https://example.com/long/path"

@pytest.mark.asyncio
async def test_shorten_invalid_url(async_client: AsyncClient):
    resp = await async_client.post("/shorten", json={"url": "not-a-url"})
    assert resp.status_code == 400

@pytest.mark.asyncio
async def test_shorten_blocked_host(async_client: AsyncClient):
    resp = await async_client.post("/shorten", json={"url": "http://localhost"})
    assert resp.status_code == 400

@pytest.mark.asyncio
async def test_shorten_with_expiry(async_client: AsyncClient):
    resp = await async_client.post("/shorten", json={
        "url": "https://example.com",
        "expires_at": "2025-12-31T23:59:59Z"
    })
    assert resp.status_code == 201
    assert resp.json()["expires_at"] is not None