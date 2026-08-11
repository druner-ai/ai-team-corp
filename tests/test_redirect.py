import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_redirect_returns_302(client: AsyncClient):
    create_resp = await client.post("/api/shorten", json={"url": "https://example.com"})
    short_code = create_resp.json()["short_code"]
    resp = await client.get(f"/{short_code}", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "https://example.com"


@pytest.mark.asyncio
async def test_redirect_increments_clicks(client: AsyncClient):
    create_resp = await client.post("/api/shorten", json={"url": "https://example.com"})
    short_code = create_resp.json()["short_code"]
    await client.get(f"/{short_code}", follow_redirects=False)
    stats_resp = await client.get(f"/api/stats/{short_code}")
    assert stats_resp.status_code == 200
    assert stats_resp.json()["clicks"] == 1
    await client.get(f"/{short_code}", follow_redirects=False)
    stats_resp = await client.get(f"/api/stats/{short_code}")
    assert stats_resp.json()["clicks"] == 2


@pytest.mark.asyncio
async def test_redirect_nonexistent_returns_404(client: AsyncClient):
    resp = await client.get("/nonexistent", follow_redirects=False)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Short link not found"
