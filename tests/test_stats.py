import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_stats_success(client: AsyncClient):
    # Create a link
    create_resp = await client.post("/api/v1/shorten", json={"url": "https://example.com"})
    short_code = create_resp.json()["short_code"]

    # Access it twice
    await client.get(f"/{short_code}")
    await client.get(f"/{short_code}")

    # Get stats
    stats_resp = await client.get(f"/api/v1/{short_code}/stats")
    assert stats_resp.status_code == 200
    data = stats_resp.json()
    assert data["short_code"] == short_code
    assert data["clicks_total"] == 2
    assert data["last_click_at"] is not None


@pytest.mark.asyncio
async def test_get_stats_not_found(client: AsyncClient):
    response = await client.get("/api/v1/nonexistent/stats")
    assert response.status_code == 404
