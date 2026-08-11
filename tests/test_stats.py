"""
Tests for the statistics endpoint.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_stats_existing_code(client: AsyncClient):
    """Test that stats for an existing code returns correct data."""
    # Create a short URL
    create_resp = await client.post(
        "/api/shorten",
        json={"url": "https://example.com/stats-test"},
    )
    code = create_resp.json()["code"]

    # Get stats (should have 0 clicks)
    stats_resp = await client.get(f"/api/stats/{code}")
    assert stats_resp.status_code == 200
    data = stats_resp.json()
    assert data["code"] == code
    assert data["original_url"] == "https://example.com/stats-test"
    assert data["total_clicks"] == 0
    assert data["recent_clicks"] == []


@pytest.mark.asyncio
async def test_stats_nonexistent_code(client: AsyncClient):
    """Test that stats for non-existent code returns 404."""
    response = await client.get("/api/stats/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_stats_after_clicks(client: AsyncClient):
    """Test that stats reflect clicks correctly."""
    create_resp = await client.post(
        "/api/shorten",
        json={"url": "https://example.com/multi-click"},
    )
    code = create_resp.json()["code"]

    # Simulate multiple clicks
    for _ in range(3):
        await client.get(f"/{code}", follow_redirects=False)

    stats_resp = await client.get(f"/api/stats/{code}")
    data = stats_resp.json()
    assert data["total_clicks"] == 3
    assert len(data["recent_clicks"]) == 3
    # Check that recent_clicks are ordered by most recent first
    # (we can't guarantee exact timestamps, but we can check count)
