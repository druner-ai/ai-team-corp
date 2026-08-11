import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_stats_returns_click_data(async_client: AsyncClient):
    payload = {"original_url": "https://example.com"}
    resp = await async_client.post("/api/v1/urls", json=payload)
    slug = resp.json()["slug"]

    # Simulate two visits
    await async_client.get(f"/r/{slug}", follow_redirects=False)
    await async_client.get(f"/r/{slug}", follow_redirects=False)

    stats_resp = await async_client.get(f"/api/v1/urls/{slug}/stats")
    assert stats_resp.status_code == 200
    data = stats_resp.json()
    assert data["total_clicks"] == 2
    assert len(data["recent_clicks"]) == 2
    assert data["slug"] == slug
    assert data["original_url"] == "https://example.com"


@pytest.mark.asyncio
async def test_stats_not_found(async_client: AsyncClient):
    response = await async_client.get("/api/v1/urls/unknown/stats")
    assert response.status_code == 404
