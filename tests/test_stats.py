"""
Tests for the GET /api/v1/stats/{short_code} endpoint.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_stats_success(client: AsyncClient) -> None:
    """Test successful retrieval of URL statistics."""
    # Create a short URL
    create_response = await client.post(
        "/api/v1/shorten",
        json={"url": "https://example.com/stats-test"},
    )
    assert create_response.status_code == 201
    data = create_response.json()
    short_code = data["short_code"]

    # Get stats
    response = await client.get(f"/api/v1/stats/{short_code}")
    assert response.status_code == 200
    stats = response.json()
    assert stats["short_code"] == short_code
    assert stats["original_url"] == "https://example.com/stats-test"
    assert stats["clicks"] == 0
    assert "created_at" in stats


@pytest.mark.asyncio
async def test_stats_not_found(client: AsyncClient) -> None:
    """Test that stats for non-existent short code returns 404."""
    response = await client.get("/api/v1/stats/nonexistent")
    assert response.status_code == 404
    assert response.json()["detail"] == "Short code not found"


@pytest.mark.asyncio
async def test_stats_after_clicks(client: AsyncClient) -> None:
    """Test that stats reflect click count after redirects."""
    # Create a short URL
    create_response = await client.post(
        "/api/v1/shorten",
        json={"url": "https://example.com/click-stats"},
    )
    short_code = create_response.json()["short_code"]

    # Perform 3 redirects
    for _ in range(3):
        await client.get(f"/{short_code}", follow_redirects=False)

    # Check stats
    response = await client.get(f"/api/v1/stats/{short_code}")
    assert response.status_code == 200
    assert response.json()["clicks"] == 3
