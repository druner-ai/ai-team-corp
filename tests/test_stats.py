"""
Tests for GET /stats/{code} endpoint.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_stats_success(client: AsyncClient):
    """Test retrieving statistics for an existing short URL."""
    create_resp = await client.post(
        "/shorten",
        json={"url": "https://example.com/stats-test"},
    )
    code = create_resp.json()["code"]

    response = await client.get(f"/stats/{code}")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == code
    assert data["original_url"] == "https://example.com/stats-test"
    assert "created_at" in data
    assert data["clicks"] == 0


@pytest.mark.anyio
async def test_stats_not_found(client: AsyncClient):
    """Test that stats for a non-existent code returns 404."""
    response = await client.get("/stats/nonexistent")
    assert response.status_code == 404
    assert response.json()["detail"] == "Short URL not found."


@pytest.mark.anyio
async def test_stats_after_clicks(client: AsyncClient):
    """Test that stats reflect clicks after redirects."""
    create_resp = await client.post(
        "/shorten",
        json={"url": "https://example.com/after-clicks"},
    )
    code = create_resp.json()["code"]

    # Simulate 3 clicks
    for _ in range(3):
        await client.get(f"/{code}", follow_redirects=False)

    response = await client.get(f"/stats/{code}")
    assert response.status_code == 200
    assert response.json()["clicks"] == 3
