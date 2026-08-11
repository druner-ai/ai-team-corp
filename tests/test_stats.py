"""Tests for GET /api/v1/links/{short_code}/stats endpoint."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_stats_existing_code(client: AsyncClient):
    """System MUST return stats for an existing short_code."""
    # Create a link first
    payload = {"original_url": "https://example.com"}
    create_resp = await client.post("/api/v1/links/shorten", json=payload)
    assert create_resp.status_code == 201
    short_code = create_resp.json()["short_code"]

    # Get stats
    resp = await client.get(f"/api/v1/links/{short_code}/stats")
    assert resp.status_code == 200
    data = resp.json()
    # Validate structure
    assert "short_code" in data
    assert data["short_code"] == short_code
    assert "original_url" in data
    assert data["original_url"] == payload["original_url"]
    assert "created_at" in data
    assert "clicks_count" in data
    # clicks_count should be an integer >=0
    assert isinstance(data["clicks_count"], int)
    assert data["clicks_count"] >= 0


@pytest.mark.asyncio
async def test_stats_nonexistent_code(client: AsyncClient):
    """System MUST return 404 for a non-existent short_code."""
    resp = await client.get("/api/v1/links/nonexistent/stats")
    assert resp.status_code == 404
