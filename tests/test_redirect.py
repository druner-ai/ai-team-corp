"""
Tests for the redirect endpoint.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_redirect_existing_code(client: AsyncClient):
    """Test that a valid short code redirects to the original URL."""
    # First create a short URL
    create_resp = await client.post(
        "/api/shorten",
        json={"url": "https://example.com/target"},
    )
    assert create_resp.status_code == 201
    code = create_resp.json()["code"]

    # Follow redirect (httpx default follows redirects, we need to disable)
    # We'll send a GET with follow_redirects=False
    redirect_resp = await client.get(f"/{code}", follow_redirects=False)
    assert redirect_resp.status_code == 307
    assert redirect_resp.headers["location"] == "https://example.com/target"


@pytest.mark.asyncio
async def test_redirect_nonexistent_code(client: AsyncClient):
    """Test that a non-existent code returns 404."""
    response = await client.get("/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_redirect_records_click(client: AsyncClient):
    """Test that a click is recorded after redirect."""
    create_resp = await client.post(
        "/api/shorten",
        json={"url": "https://example.com/click-test"},
    )
    code = create_resp.json()["code"]

    # Perform redirect
    await client.get(f"/{code}", follow_redirects=False)

    # Check stats
    stats_resp = await client.get(f"/api/stats/{code}")
    assert stats_resp.status_code == 200
    data = stats_resp.json()
    assert data["total_clicks"] == 1
    assert len(data["recent_clicks"]) == 1
