import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_shorten_url(client: AsyncClient):
    response = await client.post("/shorten", json={"url": "https://example.com"})
    assert response.status_code == 201
    data = response.json()
    assert "short_code" in data
    assert data["original_url"] == "https://example.com"
    assert data["visits"] == 0
    assert data["short_url"].startswith("http://test/")


@pytest.mark.asyncio
async def test_redirect_from_short_code(client: AsyncClient):
    # First create a short URL
    create_resp = await client.post("/shorten", json={"url": "https://example.org"})
    assert create_resp.status_code == 201
    short_code = create_resp.json()["short_code"]

    # Then request redirection
    redirect_resp = await client.get(f"/{short_code}", follow_redirects=False)
    assert redirect_resp.status_code == 200  # Our endpoint returns JSON with redirect info, not actual redirect
    redirect_data = redirect_resp.json()
    assert redirect_data["status_code"] == 301
    assert redirect_data["url"] == "https://example.org"

    # Verify that visits increased
    stats_resp = await client.get(f"/stats/{short_code}")
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["visits"] >= 1


@pytest.mark.asyncio
async def test_short_code_not_found(client: AsyncClient):
    response = await client.get("/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_duplicate_url_creates_new_code(client: AsyncClient):
    resp1 = await client.post("/shorten", json={"url": "https://duplicate.com"})
    resp2 = await client.post("/shorten", json={"url": "https://duplicate.com"})
    assert resp1.status_code == 201
    assert resp2.status_code == 201
    assert resp1.json()["short_code"] != resp2.json()["short_code"]
