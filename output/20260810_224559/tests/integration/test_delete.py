"""
Integration tests for DELETE /{short_id} endpoint.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_delete_success(client: AsyncClient):
    """Should soft-delete and return 204."""
    # Create
    resp = await client.post("/v1/shorten", json={"url": "https://example.org/delete"})
    short_id = resp.json()["short_id"]

    # Delete
    del_resp = await client.delete(f"/v1/{short_id}")
    assert del_resp.status_code == 204

    # Verify not found on GET
    get_resp = await client.get(f"/v1/{short_id}")
    assert get_resp.status_code == 404

    # Verify stats also 404
    stats_resp = await client.get(f"/v1/stats/{short_id}")
    assert stats_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent(client: AsyncClient):
    """Should return 404 when deleting non-existent short_id."""
    resp = await client.delete("/v1/nonexist")
    assert resp.status_code == 404