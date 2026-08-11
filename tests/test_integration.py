import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_full_lifecycle(client: AsyncClient):
    # Create
    create_resp = await client.post("/shorten", json={"url": "https://lifecycle.com"})
    assert create_resp.status_code == 201
    short_code = create_resp.json()["short_code"]
    # Redirect
    redirect_resp = await client.get(f"/{short_code}", follow_redirects=False)
    assert redirect_resp.status_code == 302
    # Stats
    stats_resp = await client.get(f"/stats/{short_code}")
    assert stats_resp.status_code == 200
    assert stats_resp.json()["clicks"] == 1
    # Delete
    delete_resp = await client.delete(f"/{short_code}")
    assert delete_resp.status_code == 204
    # Verify delete
    get_resp = await client.get(f"/{short_code}")
    assert get_resp.status_code == 404

@pytest.mark.asyncio
async def test_multiple_redirects_accumulate_clicks(client: AsyncClient):
    create_resp = await client.post("/shorten", json={"url": "https://clicks-accumulate.com"})
    short_code = create_resp.json()["short_code"]
    for _ in range(3):
        await client.get(f"/{short_code}", follow_redirects=False)
    stats_resp = await client.get(f"/stats/{short_code}")
    assert stats_resp.json()["clicks"] == 3

@pytest.mark.asyncio
async def test_custom_code_and_redirect(client: AsyncClient):
    payload = {"url": "https://custom-redirect.com", "custom_code": "mycustom"}
    create_resp = await client.post("/shorten", json=payload)
    assert create_resp.status_code == 201
    assert create_resp.json()["short_code"] == "mycustom"
    redirect_resp = await client.get("/mycustom", follow_redirects=False)
    assert redirect_resp.status_code == 302
    assert redirect_resp.headers["location"] == "https://custom-redirect.com"
