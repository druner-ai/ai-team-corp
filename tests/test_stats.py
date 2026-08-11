"""
Tests for GET /api/urls/{short_code}/stats endpoint.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_stats_success(client: AsyncClient):
    """Test getting statistics for an existing URL."""
    # Create a short URL
    create_resp = await client.post(
        "/api/urls",
        json={"original_url": "https://example.com/stats-test"},
    )
    short_code = create_resp.json()["short_code"]

    # Get stats
    response = await client.get(f"/api/urls/{short_code}/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["short_code"] == short_code
    assert "clicks_count" in data
    assert "created_at" in data
    assert "recent_clicks" in data


@pytest.mark.asyncio
async def test_get_stats_not_found(client: AsyncClient):
    """Test stats for non-existent URL returns 404."""
    response = await client.get("/api/urls/nonexistent/stats")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_stats_with_limit(client: AsyncClient):
    """Test stats with custom limit parameter."""
    create_resp = await client.post(
        "/api/urls",
        json={"original_url": "https://example.com/limit-test"},
    )
    short_code = create_resp.json()["short_code"]

    response = await client.get(f"/api/urls/{short_code}/stats?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data["recent_clicks"]) <= 5


@pytest.mark.asyncio
async def test_get_stats_invalid_limit(client: AsyncClient):
    """Test stats with invalid limit returns 422."""
    create_resp = await client.post(
        "/api/urls",
        json={"original_url": "https://example.com/invalid-limit"},
    )
    short_code = create_resp.json()["short_code"]

    response = await client.get(f"/api/urls/{short_code}/stats?limit=0")
    assert response.status_code == 422

    response = await client.get(f"/api/urls/{short_code}/stats?limit=101")
    assert response.status_code == 422
