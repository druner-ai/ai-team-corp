"""Tests for GET /{short_code} redirect endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_redirect_existing_code(client: AsyncClient) -> None:
    """Should redirect to original URL and increment clicks."""
    # First create a short link
    create_resp = await client.post("/shorten", json={"url": "https://example.com"})
    assert create_resp.status_code == 200
    short_code = create_resp.json()["short_code"]

    # Follow redirect (httpx default follows redirects, we need to disable)
    # Use follow_redirects=False to inspect the redirect response
    redirect_resp = await client.get(f"/{short_code}", follow_redirects=False)
    assert redirect_resp.status_code == 302
    assert redirect_resp.headers["location"] == "https://example.com"

    # Check that clicks increased
    stats_resp = await client.get(f"/stats/{short_code}")
    assert stats_resp.status_code == 200
    assert stats_resp.json()["clicks"] == 1


@pytest.mark.asyncio
async def test_redirect_nonexistent_code(client: AsyncClient) -> None:
    """Should return 404 for unknown short code."""
    response = await client.get("/nonexistent", follow_redirects=False)
    assert response.status_code == 404
    assert response.json()["detail"] == "Short link not found"
