import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_delete(async_client: AsyncClient):
    create_resp = await async_client.post("/shorten", json={"url": "https://example.com"})
    short_id = create_resp.json()["short_id"]
    del_resp = await async_client.delete(f"/{short_id}")
    assert del_resp.status_code == 204
    redirect_resp = await async_client.get(f"/{short_id}", follow_redirects=False)
    assert redirect_resp.status_code == 404