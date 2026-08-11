"""Tests for GET /stats/{short_code} endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_stats_existing_code(client: AsyncClient) -> None:
    """Should return statistics for an existing short code."""
    create_resp = await client.post("/shorten", json={"url": "https://example.com"})
    assert create_resp.status_code == 200
    short_code = create_resp.json()["short_code"]

    stats_resp = await client.get(f"/stats/{short_code}")
    assert stats_resp.status_code == 200
    data = stats_resp.json()
    assert data["short_code"] == short_code
    assert data["original_url"] == "https://example.com"
    assert data["clicks"] == 0
    assert data["created_at"] is not None
    assert data["last_visited_at"] is None


@pytest.mark.asyncio
async def test_stats_nonexistent_code(client: AsyncClient) -> None:
    """Should return 404 for unknown short code."""
    response = await client.get("/stats/nonexistent")
    assert response.status_code == 404
    assert response.json()["detail"] == "Short link not found"


@pytest.mark.asyncio
async def test_stats_after_redirect(client: AsyncClient) -> None:
    """Should show updated clicks and last_visited_at after a redirect."""
    create_resp = await client.post("/shorten", json={"url": "https://example.com"})
    short_code = create_resp.json()["short_code"]

    # Perform a redirect
    await client.get(f"/{short_code}", follow_redirects=False)

    stats_resp = await client.get(f"/stats/{short_code}")
    data = stats_resp.json()
    assert data["clicks"] == 1
    assert data["last_visited_at"] is not None
