"""Tests for POST /shorten endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_shorten_valid_url(client: AsyncClient) -> None:
    """Should create a short link for a valid URL."""
    response = await client.post("/shorten", json={"url": "https://example.com"})
    assert response.status_code == 200
    data = response.json()
    assert "short_code" in data
    assert "short_url" in data
    assert data["original_url"] == "https://example.com"
    assert data["short_url"].startswith("http://test/")


@pytest.mark.asyncio
async def test_shorten_invalid_url(client: AsyncClient) -> None:
    """Should return 422 for invalid URL."""
    response = await client.post("/shorten", json={"url": "not-a-url"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_shorten_missing_field(client: AsyncClient) -> None:
    """Should return 422 when url field is missing."""
    response = await client.post("/shorten", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_shorten_url_too_long(client: AsyncClient) -> None:
    """Should reject URLs exceeding max length."""
    long_url = "https://example.com/" + "a" * 3000
    response = await client.post("/shorten", json={"url": long_url})
    assert response.status_code == 422
