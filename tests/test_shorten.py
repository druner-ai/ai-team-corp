"""
Tests for the URL shortening endpoint.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_shorten_valid_url(client: AsyncClient):
    """Test shortening a valid URL returns 201 and correct fields."""
    response = await client.post(
        "/api/shorten",
        json={"url": "https://example.com/very/long/path?query=1"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "code" in data
    assert len(data["code"]) == 6
    assert data["short_url"].startswith("http://")
    assert data["original_url"] == "https://example.com/very/long/path?query=1"


@pytest.mark.asyncio
async def test_shorten_invalid_url(client: AsyncClient):
    """Test that an invalid URL returns 422."""
    response = await client.post(
        "/api/shorten",
        json={"url": "not-a-valid-url"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_shorten_missing_body(client: AsyncClient):
    """Test that missing request body returns 422."""
    response = await client.post("/api/shorten", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_shorten_empty_url(client: AsyncClient):
    """Test that empty URL returns 422."""
    response = await client.post("/api/shorten", json={"url": ""})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_shorten_url_too_long(client: AsyncClient):
    """Test that URL exceeding max length returns 422."""
    long_url = "https://example.com/" + "a" * 2048
    response = await client.post("/api/shorten", json={"url": long_url})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_shorten_generates_unique_codes(client: AsyncClient):
    """Test that multiple shortenings produce different codes."""
    codes = set()
    for _ in range(5):
        response = await client.post(
            "/api/shorten",
            json={"url": "https://example.com"},
        )
        assert response.status_code == 201
        codes.add(response.json()["code"])
    assert len(codes) == 5  # All unique
