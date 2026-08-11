import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_short_url(app: AsyncClient):
    payload = {"url": "https://example.com/very/long/path"}
    response = await app.post("/api/v1/shorten", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "short_id" in data
    assert data["original_url"] == payload["url"]
    assert data["short_url"].startswith("https://")

@pytest.mark.asyncio
async def test_invalid_url_rejection(app: AsyncClient):
    payload = {"url": "ftp://invalid"}
    response = await app.post("/api/v1/shorten", json=payload)
    assert response.status_code == 400