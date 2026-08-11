import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_redirect_valid_id(async_client: AsyncClient):
    create_resp = await async_client.post("/shorten", json={"url": "https://example.com"})
    short_id = create_resp.json()["short_id"]
    resp = await async_client.get(f"/{short_id}", follow_redirects=False)
    assert resp.status_code == 301
    assert resp.headers["location"] == "https://example.com"

@pytest.mark.asyncio
async def test_redirect_not_found(async_client: AsyncClient):
    resp = await async_client.get("/abc1234", follow_redirects=False)
    assert resp.status_code == 404

@pytest.mark.asyncio
async def test_redirect_id_format(async_client: AsyncClient):
    resp = await async_client.get("/short", follow_redirects=False)
    assert resp.status_code == 400