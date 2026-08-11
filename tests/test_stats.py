import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_stats_existing_code(client: AsyncClient):
    create_resp = await client.post(
        "/api/shorten", json={"url": "https://example.com"}
    )
    code = create_resp.json()["code"]

    stats_resp = await client.get(f"/api/stats/{code}")
    assert stats_resp.status_code == 200
    data = stats_resp.json()
    assert data["code"] == code
    assert data["original_url"] == "https://example.com"
    assert data["clicks"] == 0
    assert "created_at" in data
    assert data["last_clicked_at"] is None


@pytest.mark.asyncio
async def test_stats_nonexistent_code(client: AsyncClient):
    response = await client.get("/api/stats/nonexistent")
    assert response.status_code == 404
