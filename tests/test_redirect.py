import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta

@pytest.mark.asyncio
async def test_redirect_valid_url(client: AsyncClient):
    # Create link
    create_resp = await client.post("/shorten", json={"url": "https://redirect-test.com"})
    assert create_resp.status_code == 201
    short_code = create_resp.json()["short_code"]
    # Redirect
    response = await client.get(f"/{short_code}", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "https://redirect-test.com"

@pytest.mark.asyncio
async def test_redirect_increments_clicks(client: AsyncClient):
    create_resp = await client.post("/shorten", json={"url": "https://click-counter.com"})
    short_code = create_resp.json()["short_code"]
    # First redirect
    await client.get(f"/{short_code}", follow_redirects=False)
    # Second redirect
    await client.get(f"/{short_code}", follow_redirects=False)
    # Check stats
    stats_resp = await client.get(f"/stats/{short_code}")
    assert stats_resp.status_code == 200
    assert stats_resp.json()["clicks"] == 2

@pytest.mark.asyncio
async def test_redirect_not_found(client: AsyncClient):
    response = await client.get("/nonexistent")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_redirect_expired_link(client: AsyncClient):
    past = (datetime.utcnow() - timedelta(days=1)).isoformat()
    create_resp = await client.post("/shorten", json={"url": "https://expired.com", "expires_at": past})
    short_code = create_resp.json()["short_code"]
    response = await client.get(f"/{short_code}")
    assert response.status_code == 410
