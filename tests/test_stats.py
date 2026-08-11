"""Tests for GET /api/stats/{short_code}."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_stats_for_existing_link(client: AsyncClient):
    """System MUST return 200 with full stats for an existing link."""
    create_resp = await client.post("/api/shorten", json={"url": "https://example.com"})
    short_code = create_resp.json()["short_code"]

    resp = await client.get(f"/api/stats/{short_code}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["short_code"] == short_code
    assert data["original_url"].rstrip("/") == "https://example.com"
    assert "created_at" in data
    assert data["expires_at"] is None
    assert data["is_active"] is True
    assert data["total_clicks"] == 0
    assert data["last_click_at"] is None
    assert data["clicks_today"] == 0
    assert data["clicks_last_7_days"] == 0


@pytest.mark.asyncio
async def test_stats_after_clicks(client: AsyncClient):
    """System MUST reflect click counts after redirects."""
    create_resp = await client.post("/api/shorten", json={"url": "https://example.com"})
    short_code = create_resp.json()["short_code"]

    # Perform a redirect
    await client.get(f"/{short_code}", follow_redirects=False)

    resp = await client.get(f"/api/stats/{short_code}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_clicks"] == 1
    assert data["last_click_at"] is not None
    assert data["clicks_today"] == 1
    assert data["clicks_last_7_days"] == 1


@pytest.mark.asyncio
async def test_stats_not_found(client: AsyncClient):
    """System MUST return 404 for a non-existent short code."""
    resp = await client.get("/api/stats/nonexistent")
    assert resp.status_code == 404
