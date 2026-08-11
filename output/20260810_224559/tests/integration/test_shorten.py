"""
Integration tests for POST /shorten endpoint.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_shorten_success(client: AsyncClient):
    """Should return 201 and short_url."""
    payload = {"url": "https://example.com/some/long/path"}
    response = await client.post("/v1/shorten", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "short_id" in data
    assert "short_url" in data
    assert "original_url" in data
    assert data["original_url"] == payload["url"]
    assert data["short_url"].startswith("http://test/")  # base_url is test


@pytest.mark.asyncio
async def test_shorten_validation_error(client: AsyncClient):
    """Should return 422 for invalid URL."""
    response = await client.post("/v1/shorten", json={"url": "not_a_url"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_shorten_rate_limit(monkeypatch, client: AsyncClient):
    """Should return 429 when rate limit is exceeded."""
    # Reduce limit for test
    from src.middleware.rate_limit import settings
    monkeypatch.setattr(settings, "rate_limit_requests", 2)
    monkeypatch.setattr(settings, "rate_limit_window", 10)

    # Perform two requests successfully
    for _ in range(2):
        resp = await client.post("/v1/shorten", json={"url": "https://example.com"})
        assert resp.status_code == 201

    # Third should fail with 429
    resp = await client.post("/v1/shorten", json={"url": "https://example.com"})
    assert resp.status_code == 429
    assert "Rate limit exceeded" in resp.json()["detail"]