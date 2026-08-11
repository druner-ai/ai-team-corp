"""
Integration tests for URL shortener API.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_short_url(client: AsyncClient):
    response = await client.post("/shorten", json={"url": "https://example.com"})
    assert response.status_code == 201
    data = response.json()
    assert "slug" in data
    assert data["original_url"] == "https://example.com/"
    assert data["short_url"].startswith("http://test/")


@pytest.mark.asyncio
async def test_create_duplicate_slug(client: AsyncClient):
    await client.post("/shorten", json={"url": "https://example.com", "custom_slug": "test"})
    response = await client.post("/shorten", json={"url": "https://example.org", "custom_slug": "test"})
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_redirect(client: AsyncClient):
    # Create a short URL first
    create_resp = await client.post("/shorten", json={"url": "https://example.com"})
    slug = create_resp.json()["slug"]
    response = await client.get(f"/{slug}", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com/"


@pytest.mark.asyncio
async def test_redirect_not_found(client: AsyncClient):
    response = await client.get("/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_stats(client: AsyncClient):
    # Create and click a link
    create_resp = await client.post("/shorten", json={"url": "https://example.com"})
    slug = create_resp.json()["slug"]
    await client.get(f"/{slug}")
    response = await client.get(f"/stats/{slug}")
    assert response.status_code == 200
    data = response.json()
    assert data["total_clicks"] == 1
    assert len(data["clicks"]) == 1
