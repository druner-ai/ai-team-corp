import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_redirect_success(async_client: AsyncClient):
    # Create a short URL
    payload = {"original_url": "https://example.com/target"}
    resp = await async_client.post("/api/v1/urls", json=payload)
    slug = resp.json()["slug"]

    # Perform redirect
    redir = await async_client.get(f"/r/{slug}", follow_redirects=False)
    assert redir.status_code == 302
    assert redir.headers["location"] == "https://example.com/target"


@pytest.mark.asyncio
async def test_redirect_not_found(async_client: AsyncClient):
    response = await async_client.get("/r/nonexistent", follow_redirects=False)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_redirect_records_click(async_client: AsyncClient):
    payload = {"original_url": "https://example.com"}
    resp = await async_client.post("/api/v1/urls", json=payload)
    slug = resp.json()["slug"]

    # Trigger a redirect, which schedules a background task to record the click
    await async_client.get(f"/r/{slug}", follow_redirects=False)

    # Verify stats were recorded (background task runs synchronously in test env)
    stats_resp = await async_client.get(f"/api/v1/urls/{slug}/stats")
    assert stats_resp.status_code == 200
    data = stats_resp.json()
    assert data["total_clicks"] == 1
    assert len(data["recent_clicks"]) == 1
