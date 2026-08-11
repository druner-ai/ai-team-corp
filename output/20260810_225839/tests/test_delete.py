"""
Tests for DELETE /{short_code} endpoint.
"""
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_delete_success(client: AsyncClient):
    """Should soft-delete a URL and return 204."""
    create_resp = await client.post("/shorten/", json={"url": "https://example.com"})
    short_code = create_resp.json()["short_code"]
    resp = await client.delete(f"/{short_code}")
    assert resp.status_code == 204
    # Verify it's no longer accessible
    get_resp = await client.get(f"/{short_code}", follow_redirects=False)
    assert get_resp.status_code == 404

@pytest.mark.asyncio
async def test_delete_nonexistent(client: AsyncClient):
    """Should return 404 for unknown code."""
    resp = await client.delete("/nonexistent")
    assert resp.status_code == 404

@pytest.mark.asyncio
async def test_delete_twice(client: AsyncClient):
    """Deleting twice should return 404 second time."""
    create_resp = await client.post("/shorten/", json={"url": "https://example.com"})
    short_code = create_resp.json()["short_code"]
    await client.delete(f"/{short_code}")
    resp = await client.delete(f"/{short_code}")
    assert resp.status_code == 404