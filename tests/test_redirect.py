"""Tests for GET /{short_code} redirect endpoint."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_redirect_valid_code(client: AsyncClient):
    """System MUST redirect to original URL with 307 status."""
    # First, create a short link
    create_resp = await client.post("/api/v1/links/shorten", json={"original_url": "https://example.com"})
    assert create_resp.status_code == 201
    short_code = create_resp.json()["short_code"]

    # Now request the redirect
    resp = await client.get(f"/{short_code}", follow_redirects=False)
    assert resp.status_code == 307
    assert resp.headers["location"] == "https://example.com"


@pytest.mark.asyncio
async def test_redirect_not_found(client: AsyncClient):
    """System MUST return 404 for non-existent short code."""
    resp = await client.get("/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_redirect_increments_click_count(client: AsyncClient):
    """Each redirect MUST be recorded as a click in statistics."""
    # Create a link
    create_resp = await client.post("/api/v1/links/shorten", json={"original_url": "https://example.com"})
    short_code = create_resp.json()["short_code"]

    # Initial stats should show 0 clicks
    stats_resp0 = await client.get(f"/api/v1/links/{short_code}/stats")
    assert stats_resp0.status_code == 200
    initial_clicks = stats_resp0.json()["clicks_count"]

    # Perform a redirect
    await client.get(f"/{short_code}", follow_redirects=False)

    # Stats should show incremented clicks
    stats_resp1 = await client.get(f"/api/v1/links/{short_code}/stats")
    assert stats_resp1.status_code == 200
    assert stats_resp1.json()["clicks_count"] == initial_clicks + 1
