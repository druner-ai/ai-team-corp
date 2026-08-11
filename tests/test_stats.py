import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_stats_returns_url_info(client: AsyncClient):
    create_resp = await client.post("/api/shorten", json={"url": "https://example.com"})
    short_code = create_resp.json()["short_code"]
    resp = await client.get(f"/api/stats/{short_code}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["short_code"] == short_code
    assert data["original_url"] == "https://example.com"
    assert data["clicks"] == 0
    assert "created_at" in data


@pytest.mark.asyncio
async def test_stats_nonexistent_code_returns_404(client: AsyncClient):
    resp = await client.get("/api/stats/nonexistent")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Short link not found"
