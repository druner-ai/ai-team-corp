import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_redirect_success(client: AsyncClient):
    """Test that a valid short code redirects to the original URL."""
    # First create a link
    create_resp = await client.post(
        "/api/links", json={"url": "https://example.com/target"}
    )
    assert create_resp.status_code == 201
    short_code = create_resp.json()["short_code"]

    # Now request the redirect
    redirect_resp = await client.get(f"/{short_code}", follow_redirects=False)
    assert redirect_resp.status_code == 302
    assert redirect_resp.headers["location"] == "https://example.com/target"


@pytest.mark.asyncio
async def test_redirect_not_found(client: AsyncClient):
    """Test that a non-existent short code returns 404."""
    response = await client.get("/nonexistent")
    assert response.status_code == 404
    assert response.json()["detail"] == "Short link not found"


@pytest.mark.asyncio
async def test_redirect_increments_clicks(client: AsyncClient):
    """Test that the click counter is incremented on each redirect."""
    # Create link
    create_resp = await client.post(
        "/api/links", json={"url": "https://example.com/count"}
    )
    short_code = create_resp.json()["short_code"]

    # Initial stats
    stats_resp = await client.get(f"/api/links/{short_code}/stats")
    assert stats_resp.status_code == 200
    assert stats_resp.json()["clicks"] == 0

    # Perform redirect
    await client.get(f"/{short_code}", follow_redirects=False)

    # Check stats again
    stats_resp = await client.get(f"/api/links/{short_code}/stats")
    assert stats_resp.status_code == 200
    assert stats_resp.json()["clicks"] == 1
