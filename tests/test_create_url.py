"""
Tests for POST /api/urls endpoint.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_short_url_success(client: AsyncClient):
    """Test successful creation of a short URL."""
    response = await client.post(
        "/api/urls",
        json={"original_url": "https://example.com/very/long/path"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "short_code" in data
    assert "short_url" in data
    assert data["original_url"] == "https://example.com/very/long/path"
    assert len(data["short_code"]) == 6


@pytest.mark.asyncio
async def test_create_short_url_with_custom_code(client: AsyncClient):
    """Test creation with a custom short code."""
    response = await client.post(
        "/api/urls",
        json={
            "original_url": "https://example.com",
            "custom_code": "mycode",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["short_code"] == "mycode"


@pytest.mark.asyncio
async def test_create_short_url_duplicate_custom_code(client: AsyncClient):
    """Test that duplicate custom code returns 409 Conflict."""
    # Create first
    await client.post(
        "/api/urls",
        json={"original_url": "https://example1.com", "custom_code": "duplicate"},
    )
    # Try duplicate
    response = await client.post(
        "/api/urls",
        json={"original_url": "https://example2.com", "custom_code": "duplicate"},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_create_short_url_invalid_url(client: AsyncClient):
    """Test that invalid URL returns 422."""
    response = await client.post(
        "/api/urls",
        json={"original_url": "not-a-valid-url"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_short_url_blocked_scheme(client: AsyncClient):
    """Test that blocked URL schemes are rejected."""
    response = await client.post(
        "/api/urls",
        json={"original_url": "file:///etc/passwd"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_short_url_missing_scheme(client: AsyncClient):
    """Test that URL without scheme gets https:// added."""
    response = await client.post(
        "/api/urls",
        json={"original_url": "example.com/page"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["original_url"] == "https://example.com/page"


@pytest.mark.asyncio
async def test_create_short_url_invalid_custom_code(client: AsyncClient):
    """Test that invalid custom code format returns 422."""
    response = await client.post(
        "/api/urls",
        json={
            "original_url": "https://example.com",
            "custom_code": "ab",  # Too short
        },
    )
    assert response.status_code == 422

    response = await client.post(
        "/api/urls",
        json={
            "original_url": "https://example.com",
            "custom_code": "invalid code!",  # Invalid characters
        },
    )
    assert response.status_code == 422
