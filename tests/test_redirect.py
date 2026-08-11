import pytest
from httpx import AsyncClient
import logging

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_redirect_success(client: AsyncClient):
    # Create a link first
    create_resp = await client.post("/links", json={"url": "https://example.com"})
    slug = create_resp.json()["slug"]
    response = await client.get(f"/{slug}", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com"


@pytest.mark.asyncio
async def test_redirect_not_found(client: AsyncClient):
    response = await client.get("/nonexistent")
    assert response.status_code == 404
    assert response.json()["detail"] == "Short link not found"


@pytest.mark.asyncio
async def test_redirect_records_click(client: AsyncClient):
    create_resp = await client.post("/links", json={"url": "https://example.com"})
    slug = create_resp.json()["slug"]
    # First redirect
    await client.get(f"/{slug}", follow_redirects=False)
    # Check stats
    stats_resp = await client.get(f"/stats/{slug}")
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["clicks_count"] == 1
    assert stats["last_click_at"] is not None
