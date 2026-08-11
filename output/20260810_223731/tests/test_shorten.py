"""
Tests for POST /shorten endpoint.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_shorten_valid_url(async_client: AsyncClient):
    payload = {"url": "https://example.com/valid/path?q=1"}
    response = await async_client.post("/shorten", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert len(data["id"]) == 7
    assert data["original_url"] == "https://example.com/valid/path?q=1"
    assert data["short_url"].startswith("http://test/")

    # Verify by retrieving redirect (should be saved)
    resp = await async_client.get(f"/{data['id']}")
    assert resp.status_code == 302
    assert resp.headers["location"] == "https://example.com/valid/path?q=1"


@pytest.mark.asyncio
async def test_shorten_invalid_url(async_client: AsyncClient):
    # Invalid scheme (Pydantic HttpUrl rejects)
    payload = {"url": "ftp://bad-scheme.com"}
    response = await async_client.post("/shorten", json=payload)
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_shorten_missing_url(async_client: AsyncClient):
    response = await async_client.post("/shorten", json={})
    assert response.status_code == 422