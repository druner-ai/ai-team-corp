"""Tests for GET /{short_code} – redirect endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_redirect_valid_url(client: AsyncClient):
    """System MUST return 302 with Location header pointing to original URL."""
    # Create a link
    create_resp = await client.post("/api/shorten", json={"url": "https://example.com"})
    short_code = create_resp.json()["short_code"]

    # Follow redirect
    resp = await client.get(f"/{short_code}", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "https://example.com"


@pytest.mark.asyncio
async def test_redirect_increments_clicks(client: AsyncClient):
    """System MUST increment click count on each redirect."""
    create_resp = await client.post("/api/shorten", json={"url": "https://example.com"})
    short_code = create_resp.json()["short_code"]

    # First redirect
    await client.get(f"/{short_code}", follow_redirects=False)

    # Check stats
    stats_resp = await client.get(f"/api/stats/{short_code}")
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["total_clicks"] == 1


@pytest.mark.asyncio
async def test_redirect_not_found(client: AsyncClient):
    """System MUST return 404 for a non-existent short code."""
    resp = await client.get("/nonexistent", follow_redirects=False)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_redirect_inactive_link(client: AsyncClient):
    """System MUST return 404 (or 410) for a soft-deleted link."""
    create_resp = await client.post("/api/shorten", json={"url": "https://example.com"})
    short_code = create_resp.json()["short_code"]

    # Delete (soft)
    await client.delete(f"/api/shorten/{short_code}")

    # Redirect must fail
    resp = await client.get(f"/{short_code}", follow_redirects=False)
    assert resp.status_code in (404, 410)


@pytest.mark.asyncio
async def test_redirect_expired_link(client: AsyncClient):
    """System MUST return 410 for an expired link."""
    # Create with past expiration
    payload = {
        "url": "https://example.com",
        "expires_at": "2020-01-01T00:00:00Z"
    }
    create_resp = await client.post("/api/shorten", json=payload)
    short_code = create_resp.json()["short_code"]

    resp = await client.get(f"/{short_code}", follow_redirects=False)
    assert resp.status_code == 410
