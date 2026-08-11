"""
Tests for POST /shorten endpoint.
"""
import pytest
from httpx import AsyncClient
from unittest.mock import patch


@pytest.mark.asyncio
async def test_create_short_url_success(client: AsyncClient, mock_redis):
    """
    Test successful short URL creation.
    """
    # Mock Redis to return None (no existing cache)
    mock_redis.get.return_value = None
    
    response = await client.post(
        "/shorten",
        json={"url": "https://example.com/very/long/path?query=1"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "short_id" in data
    assert "short_url" in data
    assert "original_url" in data
    assert "created_at" in data
    assert len(data["short_id"]) == 7
    assert data["original_url"] == "https://example.com/very/long/path?query=1"


@pytest.mark.asyncio
async def test_create_short_url_invalid_url(client: AsyncClient):
    """
    Test short URL creation with invalid URL.
    """
    response = await client.post(
        "/shorten",
        json={"url": "not-a-valid-url"}
    )
    
    assert response.status_code == 422  # Pydantic validation error


@pytest.mark.asyncio
async def test_create_short_url_invalid_scheme(client: AsyncClient):
    """
    Test short URL creation with disallowed URL scheme.
    """
    response = await client.post(
        "/shorten",
        json={"url": "ftp://example.com/file"}
    )
    
    assert response.status_code == 422  # Pydantic HttpUrl validation


@pytest.mark.asyncio
async def test_create_short_url_empty_body(client: AsyncClient):
    """
    Test short URL creation with empty request body.
    """
    response = await client.post(
        "/shorten",
        json={}
    )
    
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_short_url_too_long(client: AsyncClient):
    """
    Test short URL creation with URL exceeding max length.
    """
    long_url = "https://example.com/" + "a" * 2100
    response = await client.post(
        "/shorten",
        json={"url": long_url}
    )
    
    assert response.status_code == 422