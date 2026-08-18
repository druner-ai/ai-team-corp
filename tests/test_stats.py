import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_stats_for_existing_link(client: AsyncClient):
    create_resp = await client.post("/shorten", json={"url": "https://stats-test.com"})
    short_code = create_resp.json()["short_code"]
    stats_resp = await client.get(f"/stats/{short_code}")
    assert stats_resp.status_code == 200
    data = stats_resp.json()
    assert data["url"] == "https://stats-test.com"
    assert data["short_code"] == short_code
    assert data["clicks"] == 0

@pytest.mark.asyncio
async def test_stats_after_clicks(client: AsyncClient):
    create_resp = await client.post("/shorten", json={"url": "https://stats-clicks.com"})
    short_code = create_resp.json()["short_code"]
    # Simulate one click
    await client.get(f"/{short_code}", follow_redirects=False)
    stats_resp = await client.get(f"/stats/{short_code}")
    assert stats_resp.status_code == 200
    assert stats_resp.json()["clicks"] == 1

@pytest.mark.asyncio
async def test_stats_not_found(client: AsyncClient):
    response = await client.get("/stats/nonexistent")
    assert response.status_code == 404
