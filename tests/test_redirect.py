"""
Tests for GET /{code} redirect endpoint.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_redirect_success(client: AsyncClient):
    """Test that a valid short code redirects to the original URL."""
    # First, create a short URL
    create_resp = await client.post(
        "/shorten",
        json={"url": "https://example.com/target"},
    )
    code = create_resp.json()["code"]

    # Then, follow the redirect (disable auto-redirect to inspect headers)
    response = await client.get(f"/{code}", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "https://example.com/target"


@pytest.mark.anyio
async def test_redirect_not_found(client: AsyncClient):
    """Test that a non-existent code returns 404."""
    response = await client.get("/nonexistent", follow_redirects=False)
    assert response.status_code == 404
    assert response.json()["detail"] == "Short URL not found."


@pytest.mark.anyio
async def test_redirect_increments_clicks(client: AsyncClient):
    """Test that each redirect increments the click counter."""
    create_resp = await client.post(
        "/shorten",
        json={"url": "https://example.com/count-clicks"},
    )
    code = create_resp.json()["code"]

    # Perform two redirects
    await client.get(f"/{code}", follow_redirects=False)
    await client.get(f"/{code}", follow_redirects=False)

    # Check stats
    stats_resp = await client.get(f"/stats/{code}")
    assert stats_resp.status_code == 200
    assert stats_resp.json()["clicks"] == 2
