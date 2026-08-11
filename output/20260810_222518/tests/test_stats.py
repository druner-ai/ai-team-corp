"""
Tests for GET /stats/{id} endpoint.
"""
import pytest
from httpx import AsyncClient
from unittest.mock import patch


@pytest.mark.asyncio
async def test_get_stats_success(client: AsyncClient, mock_redis, test_session):
    """
    Test successful statistics retrieval.
    """
    # Setup: Create a short URL
    mock_redis.get.return_value = None
    create_response = await client.post(
        "/shorten",
        json={"url": "https://example.com/stats-test"}
    )
    short_id = create_response.json()["short_id"]
    
    # Get stats
    response = await client.get(f"/stats/{short_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["short_id"] == short_id
    assert data["original_url"] == "https://example.com/stats-test"
    assert "click_count" in data
    assert "created_at" in data
    assert data["is_active"] == True


@pytest.mark.asyncio
async def test_get_stats_not_found(client: AsyncClient, mock_redis):
    """
    Test statistics for non-existent short ID.
    """
    mock_redis.get.return_value = None
    
    response = await client.get("/stats/nonexist")
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_stats_invalid_id(client: AsyncClient):
    """
    Test statistics with invalid short ID format.
    """
    response = await client.get("/stats/ab")
    
    assert response.status_code == 404