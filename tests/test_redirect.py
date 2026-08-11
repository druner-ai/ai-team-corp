"""
Tests for GET /{short_code} redirect endpoint.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_redirect_success(client: AsyncClient):
    """Test successful redirect to original URL."""
    # Create a short URL first
    create_resp = await client.post(
        "/api/urls",
        json={"original_url": "https://example.com/target"},
    )
    assert create_resp.status_code == 201
    short_code = create_resp.json()["short_code"]

    # Follow redirect (httpx default is to follow redirects, so disable)
    response = await client.get(f"/{short_code}", follow_redirects=False)
    assert response.status_code == 301
    assert response.headers["location"] == "https://example.com/target"


@pytest.mark.asyncio
async def test_redirect_not_found(client: AsyncClient):
    """Test redirect with non-existent short code returns 404."""
    response = await client.get("/nonexistent", follow_redirects=False)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_redirect_records_click(client: AsyncClient):
    """Test that a redirect records a click in stats."""
    # Create a short URL
    create_resp = await client.post(
        "/api/urls",
        json={"original_url": "https://example.com/click-test"},
    )
    short_code = create_resp.json()["short_code"]

    # Perform redirect
    await client.get(f"/{short_code}", follow_redirects=False)

    # Wait a bit for fire-and-forget click recording
    import asyncio
    await asyncio.sleep(0.1)

    # Check stats
    stats_resp = await client.get(f"/api/urls/{short_code}/stats")
    assert stats_resp.status_code == 200
    data = stats_resp.json()
    assert data["clicks_count"] >= 1


@pytest.mark.asyncio
async def test_redirect_deactivated_url(client: AsyncClient):
    """Test that deactivated URL returns 404."""
    # Create and then deactivate
    create_resp = await client.post(
        "/api/urls",
        json={"original_url": "https://example.com/deactivate-me"},
    )
    short_code = create_resp.json()["short_code"]

    # Deactivate
    await client.delete(f"/api/urls/{short_code}")

    # Try redirect
    response = await client.get(f"/{short_code}", follow_redirects=False)
    assert response.status_code == 404
