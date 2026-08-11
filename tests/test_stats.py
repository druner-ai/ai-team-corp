import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_stats_no_clicks(client: AsyncClient):
    create_resp = await client.post(
        "/api/v1/shorten", json={"url": "https://example.com/stats"}
    )
    assert create_resp.status_code == 201
    code = create_resp.json()["code"]

    stats_resp = await client.get(f"/api/v1/stats/{code}")
    assert stats_resp.status_code == 200
    data = stats_resp.json()
    assert data["total_clicks"] == 0
    assert data["last_click_at"] is None
    assert data["top_referers"] == []
    assert data["top_user_agents"] == []


@pytest.mark.anyio
async def test_stats_with_clicks(client: AsyncClient):
    # Create
    create_resp = await client.post(
        "/api/v1/shorten", json={"url": "https://example.com/clicks"}
    )
    assert create_resp.status_code == 201
    code = create_resp.json()["code"]

    # Perform a few redirects
    for _ in range(3):
        await client.get(f"/{code}", follow_redirects=False)

    stats_resp = await client.get(f"/api/v1/stats/{code}")
    assert stats_resp.status_code == 200
    data = stats_resp.json()
    assert data["total_clicks"] == 3
    assert data["last_click_at"] is not None


@pytest.mark.anyio
async def test_stats_not_found(client: AsyncClient):
    response = await client.get("/api/v1/stats/nonexistent")
    assert response.status_code == 404
