"""
Tests for GET /api/urls/{short_code} endpoint.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_url_info_success(client: AsyncClient):
    """Test getting URL information."""
    create_resp = await client.post(
        "/api/urls",
        json={"original_url": "https://example.com/info-test"},
    )
    short_code = create_resp.json()["short_code"]

    response = await client.get(f"/api/urls/{short_code}")
    assert response.status_code == 200
    data = response.json()
    assert data["short_code"] == short_code
    assert data["original_url"] == "https://example.com/info-test"
    assert "clicks_count" in data
    assert "is_active" in data


@pytest.mark.asyncio
async def test_get_url_info_not_found(client: AsyncClient):
    """Test getting info for non-existent URL returns 404."""
    response = await client.get("/api/urls/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_url_success(client: AsyncClient):
    """Test deactivating a URL."""
    create_resp = await client.post(
        "/api/urls",
        json={"original_url": "https://example.com/delete-me"},
    )
    short_code = create_resp.json()["short_code"]

    response = await client.delete(f"/api/urls/{short_code}")
    assert response.status_code == 204

    # Verify it's deactivated
    info_resp = await client.get(f"/api/urls/{short_code}")
    assert info_resp.status_code == 200
    assert info_resp.json()["is_active"] is False


@pytest.mark.asyncio
async def test_delete_url_not_found(client: AsyncClient):
    """Test deleting non-existent URL returns 404."""
    response = await client.delete("/api/urls/nonexistent")
    assert response.status_code == 404
