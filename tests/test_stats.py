import pytest
from httpx import AsyncClient
import logging

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_stats_success(client: AsyncClient):
    create_resp = await client.post("/links", json={"url": "https://example.com"})
    slug = create_resp.json()["slug"]
    response = await client.get(f"/stats/{slug}")
    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == slug
    assert data["clicks_count"] == 0
    assert data["last_click_at"] is None


@pytest.mark.asyncio
async def test_stats_not_found(client: AsyncClient):
    response = await client.get("/stats/nonexistent")
    assert response.status_code == 404
