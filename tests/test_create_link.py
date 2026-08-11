import pytest
from httpx import AsyncClient
import logging

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_create_link_success(client: AsyncClient):
    response = await client.post("/links", json={"url": "https://example.com"})
    assert response.status_code == 201
    data = response.json()
    assert "slug" in data
    assert data["original_url"] == "https://example.com"
    assert data["short_url"].startswith("http://test/")


@pytest.mark.asyncio
async def test_create_link_invalid_url(client: AsyncClient):
    response = await client.post("/links", json={"url": "not-a-url"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_link_custom_slug(client: AsyncClient):
    response = await client.post("/links", json={"url": "https://example.com", "custom_slug": "myslug"})
    assert response.status_code == 201
    data = response.json()
    assert data["slug"] == "myslug"


@pytest.mark.asyncio
async def test_create_link_duplicate_custom_slug(client: AsyncClient):
    await client.post("/links", json={"url": "https://example.com", "custom_slug": "dup"})
    response = await client.post("/links", json={"url": "https://example.org", "custom_slug": "dup"})
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_link_invalid_custom_slug(client: AsyncClient):
    response = await client.post("/links", json={"url": "https://example.com", "custom_slug": "invalid slug!"})
    assert response.status_code == 400
    assert "Custom slug must be" in response.json()["detail"]
