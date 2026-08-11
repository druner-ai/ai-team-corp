import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_redirect_existing_code(client: AsyncClient):
    # Create a short URL first
    create_resp = await client.post(
        "/api/shorten", json={"url": "https://example.com"}
    )
    code = create_resp.json()["code"]

    # Follow redirect manually
    redirect_resp = await client.get(f"/{code}", follow_redirects=False)
    assert redirect_resp.status_code == 302
    assert redirect_resp.headers["location"] == "https://example.com"


@pytest.mark.asyncio
async def test_redirect_nonexistent_code(client: AsyncClient):
    response = await client.get("/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_redirect_increments_clicks(client: AsyncClient):
    create_resp = await client.post(
        "/api/shorten", json={"url": "https://example.com"}
    )
    code = create_resp.json()["code"]

    # First redirect
    await client.get(f"/{code}", follow_redirects=False)
    stats_resp = await client.get(f"/api/stats/{code}")
    assert stats_resp.status_code == 200
    assert stats_resp.json()["clicks"] == 1

    # Second redirect
    await client.get(f"/{code}", follow_redirects=False)
    stats_resp2 = await client.get(f"/api/stats/{code}")
    assert stats_resp2.json()["clicks"] == 2
