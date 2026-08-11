import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_stats(async_client: AsyncClient):
    create_resp = await async_client.post("/shorten", json={"url": "https://example.com"})
    short_id = create_resp.json()["short_id"]
    await async_client.get(f"/{short_id}", follow_redirects=False)
    stats_resp = await async_client.get(f"/stats/{short_id}")
    assert stats_resp.status_code == 200
    data = stats_resp.json()
    assert data["click_count"] == 1
    assert data["is_active"] is True