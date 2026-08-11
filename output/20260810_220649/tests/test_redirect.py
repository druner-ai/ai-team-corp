import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_redirect_success(app: AsyncClient):
    # First create a short URL
    payload = {"url": "https://example.com"}
    create_resp = await app.post("/api/v1/shorten", json=payload)
    assert create_resp.status_code == 201
    short_id = create_resp.json()["short_id"]

    # Redirect
    redirect_resp = await app.get(f"/api/v1/{short_id}", follow_redirects=False)
    assert redirect_resp.status_code == 302
    assert redirect_resp.headers["location"] == payload["url"]

@pytest.mark.asyncio
async def test_redirect_not_found(app: AsyncClient):
    response = await app.get("/api/v1/nonexistent", follow_redirects=False)
    assert response.status_code == 404