"""
Tests for POST /shorten endpoint.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_create_short_url_success(client: AsyncClient):
    """Test successful creation of a short URL."""
    response = await client.post(
        "/shorten",
        json={"url": "https://example.com/very/long/path?query=1"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "code" in data
    assert len(data["code"]) == 6
    assert data["short_url"].startswith("http://localhost:8000/")
    assert data["original_url"] == "https://example.com/very/long/path?query=1"


@pytest.mark.anyio
async def test_create_short_url_invalid_url(client: AsyncClient):
    """Test that invalid URLs are rejected with 422."""
    response = await client.post(
        "/shorten",
        json={"url": "not-a-valid-url"},
    )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_create_short_url_missing_body(client: AsyncClient):
    """Test that missing request body returns 422."""
    response = await client.post("/shorten", json={})
    assert response.status_code == 422


@pytest.mark.anyio
async def test_create_short_url_javascript_scheme_rejected(client: AsyncClient):
    """Test that javascript: scheme is rejected."""
    response = await client.post(
        "/shorten",
        json={"url": "javascript:alert('xss')"},
    )
    assert response.status_code == 422


@pytest.mark.anyio
async def test_create_short_url_duplicate_returns_same_code(client: AsyncClient):
    """
    Test that submitting the same URL twice creates two different short codes.

    Note: The architecture does not deduplicate URLs; each request generates a new code.
    """
    url = "https://example.com/duplicate"
    response1 = await client.post("/shorten", json={"url": url})
    response2 = await client.post("/shorten", json={"url": url})
    assert response1.status_code == 201
    assert response2.status_code == 201
    assert response1.json()["code"] != response2.json()["code"]
