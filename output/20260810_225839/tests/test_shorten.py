"""
Tests for POST /shorten endpoint.
"""
import pytest
from httpx import AsyncClient
import time

@pytest.mark.asyncio
async def test_shorten_url_success(client: AsyncClient):
    """Should create a short URL with valid data."""
    long_url = "https://example.com/very/long/path?param=value"
    response = await client.post("/shorten/", json={"url": long_url})
    assert response.status_code == 201
    data = response.json()
    assert "short_code" in data
    assert len(data["short_code"]) == 6
    assert data["original_url"] == long_url
    assert data["short_url"].startswith("http://test/")
    assert data["expires_at"] is None

@pytest.mark.asyncio
async def test_shorten_url_with_expiration(client: AsyncClient):
    """Should accept an expiration date."""
    response = await client.post("/shorten/", json={
        "url": "https://example.com",
        "expires_at": "2025-12-31T23:59:59Z"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["expires_at"] == "2025-12-31T23:59:59"

@pytest.mark.asyncio
async def test_shorten_url_invalid_url(client: AsyncClient):
    """Should reject invalid URLs."""
    response = await client.post("/shorten/", json={"url": "not_a_url"})
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_shorten_url_ssrf_blocked(client: AsyncClient):
    """Should reject URLs pointing to internal IPs."""
    response = await client.post("/shorten/", json={"url": "http://127.0.0.1/admin"})
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_shorten_url_rate_limiting(client: AsyncClient):
    """Should enforce rate limiting (using in-memory storage)."""
    # Exceed the limit (10 per minute)
    responses = []
    for _ in range(12):
        resp = await client.post("/shorten/", json={"url": "https://unique.com"})
        responses.append(resp.status_code)
    assert 429 in responses