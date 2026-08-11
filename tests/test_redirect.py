"""
Tests for the GET /{short_code} redirect endpoint.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_redirect_success(client: AsyncClient) -> None:
    """Test successful redirect to original URL."""
    # First create a short URL
    create_response = await client.post(
        "/api/v1/shorten",
        json={"url": "https://example.com/target-page"},
    )
    assert create_response.status_code == 201
    short_code = create_response.json()["short_code"]

    # Then follow the redirect (httpx follows redirects by default, so we disable it)
    response = await client.get(f"/{short_code}", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "https://example.com/target-page"


@pytest.mark.asyncio
async def test_redirect_not_found(client: AsyncClient) -> None:
    """Test that non-existent short code returns 404."""
    response = await client.get("/nonexistent")
    assert response.status_code == 404
    assert response.json()["detail"] == "Short code not found"


@pytest.mark.asyncio
async def test_redirect_increments_clicks(client: AsyncClient) -> None:
    """Test that redirect increments the click counter."""
    # Create a short URL
    create_response = await client.post(
        "/api/v1/shorten",
        json={"url": "https://example.com/click-test"},
    )
    short_code = create_response.json()["short_code"]

    # Perform redirect twice
    await client.get(f"/{short_code}", follow_redirects=False)
    await client.get(f"/{short_code}", follow_redirects=False)

    # Check stats
    stats_response = await client.get(f"/api/v1/stats/{short_code}")
    assert stats_response.status_code == 200
    assert stats_response.json()["clicks"] == 2
