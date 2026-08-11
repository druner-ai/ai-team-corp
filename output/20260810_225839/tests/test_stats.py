"""
Tests for GET /stats/{short_code} endpoint.
"""
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_stats_success(client: AsyncClient):
    """Should return statistics for a valid short code."""
    create_resp = await client.post("/shorten/", json={"url": "https://example.com"})
    short_code = create_resp.json()["short_code"]
    # Simulate a few clicks
    for _ in range(3):
        await client.get(f"/{short_code}", follow_redirects=False)
    resp = await client.get(f"/stats/{short_code}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["short_code"] == short_code
    assert data["click_count"] == 3
    assert data["is_active"] == True
    assert data["last_clicked_at"] is not None

@pytest.mark.asyncio
async def test_stats_not_found(client: AsyncClient):
    """Should return 404 for unknown code."""
    resp = await client.get("/stats/nonexistent")
    assert resp.status_code == 404

@pytest.mark.asyncio
async def test_stats_deleted(client: AsyncClient):
    """Stats endpoint returns 404 for deleted URLs."""
    create_resp = await client.post("/shorten/", json={"url": "https://example.com"})
    short_code = create_resp.json()["short_code"]
    await client.delete(f"/{short_code}")
    resp = await client.get(f"/stats/{short_code}")
    assert resp.status_code == 404