import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_short_link(client: AsyncClient):
    payload = {"url": "https://example.com/very/long/url"}
    response = await client.post("/links", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "short_code" in data
    assert "short_url" in data
    assert data["short_url"].endswith(data["short_code"])


@pytest.mark.asyncio
async def test_redirect_to_original(client: AsyncClient):
    # First create a short link
    create_resp = await client.post("/links", json={"url": "https://example.com"})
    short_code = create_resp.json()["short_code"]

    # Follow redirect (httpx default is to follow, so we disable)
    response = await client.get(f"/{short_code}", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "https://example.com"


@pytest.mark.asyncio
async def test_redirect_increments_access_count(client: AsyncClient):
    create_resp = await client.post("/links", json={"url": "https://example.org"})
    short_code = create_resp.json()["short_code"]

    # First redirect
    await client.get(f"/{short_code}", follow_redirects=False)
    # Second redirect
    await client.get(f"/{short_code}", follow_redirects=False)

    # Check stats
    stats_resp = await client.get(f"/stats/{short_code}")
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["access_count"] == 2


@pytest.mark.asyncio
async def test_stats_for_nonexistent_code(client: AsyncClient):
    response = await client.get("/stats/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_redirect_nonexistent_code(client: AsyncClient):
    response = await client.get("/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_link_with_invalid_url(client: AsyncClient):
    # Even if URL is not valid, our service accepts any string (no validation)
    payload = {"url": "not-a-valid-url"}
    response = await client.post("/links", json=payload)
    assert response.status_code == 201
