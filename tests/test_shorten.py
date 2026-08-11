"""
Tests for the POST /api/v1/shorten endpoint.
"""

import pytest
from httpx import AsyncClient

from tests.conftest import TEST_BASE_URL


@pytest.mark.asyncio
async def test_create_short_url_success(client: AsyncClient) -> None:
    """Test successful creation of a short URL."""
    response = await client.post(
        "/api/v1/shorten",
        json={"url": "https://example.com/very/long/path?query=1"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "short_code" in data
    assert len(data["short_code"]) == 6
    assert data["short_url"] == f"{TEST_BASE_URL}/{data['short_code']}"
    assert data["original_url"] == "https://example.com/very/long/path?query=1"


@pytest.mark.asyncio
async def test_create_short_url_invalid_scheme(client: AsyncClient) -> None:
    """Test that URLs with disallowed schemes are rejected."""
    response = await client.post(
        "/api/v1/shorten",
        json={"url": "ftp://example.com/file"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_short_url_missing_url(client: AsyncClient) -> None:
    """Test that request without url field is rejected."""
    response = await client.post(
        "/api/v1/shorten",
        json={},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_short_url_empty_string(client: AsyncClient) -> None:
    """Test that empty URL string is rejected."""
    response = await client.post(
        "/api/v1/shorten",
        json={"url": ""},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_short_url_too_long(client: AsyncClient) -> None:
    """Test that URLs exceeding max length are rejected."""
    long_url = "https://example.com/" + "a" * 2100
    response = await client.post(
        "/api/v1/shorten",
        json={"url": long_url},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_short_url_no_host(client: AsyncClient) -> None:
    """Test that URL without host is rejected."""
    response = await client.post(
        "/api/v1/shorten",
        json={"url": "https:///path"},
    )
    assert response.status_code == 422
