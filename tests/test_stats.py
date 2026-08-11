import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_stats_success(client: AsyncClient):
    """Test retrieving stats for an existing short link."""
    create_resp = await client.post(
        "/api/links", json={"url": "https://example.com/stats-test"}
    )
    short_code = create_resp.json()["short_code"]

    stats_resp = await client.get(f"/api/links/{short_code}/stats")
    assert stats_resp.status_code == 200
    data = stats_resp.json()
    assert data["short_code"] == short_code
    assert data["original_url"] == "https://example.com/stats-test"
    assert data["clicks"] == 0
    assert "created_at" in data


@pytest.mark.asyncio
async def test_stats_not_found(client: AsyncClient):
    """Test that stats for non-existent short code returns 404."""
    response = await client.get("/api/links/nonexistent/stats")
    assert response.status_code == 404
    assert response.json()["detail"] == "Short link not found"
