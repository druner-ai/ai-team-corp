import pytest


@pytest.mark.asyncio
async def test_stats_existing_code(client):
    create_resp = await client.post("/shorten", json={"url": "https://example.com"})
    short_code = create_resp.json()["short_code"]

    response = await client.get(f"/stats/{short_code}")
    assert response.status_code == 200
    data = response.json()
    assert data["short_code"] == short_code
    assert data["original_url"] == "https://example.com"
    assert "created_at" in data
    assert data["clicks"] == 0


@pytest.mark.asyncio
async def test_stats_nonexistent_code(client):
    response = await client.get("/stats/nonexistent")
    assert response.status_code == 404
