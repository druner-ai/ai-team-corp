"""
Tests for GET /{id} redirect endpoint.
"""
import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_redirect_success(client: AsyncClient, mock_redis, test_session):
    """
    Test successful redirect to original URL.
    """
    # Setup: Create a short URL first
    mock_redis.get.return_value = None
    create_response = await client.post(
        "/shorten",
        json={"url": "https://example.com/test"}
    )
    short_id = create_response.json()["short_id"]
    
    # Mock Redis to return cached URL for redirect
    mock_redis.get.return_value = "https://example.com/test"
    
    # Test redirect
    response = await client.get(f"/{short_id}", follow_redirects=False)
    
    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com/test"


@pytest.mark.asyncio
async def test_redirect_not_found(client: AsyncClient, mock_redis):
    """
    Test redirect with non-existent short ID.
    """
    mock_redis.get.return_value = None
    
    response = await client.get("/nonexist", follow_redirects=False)
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_redirect_invalid_id_format(client: AsyncClient):
    """
    Test redirect with invalid short ID format.
    """
    response = await client.get("/ab", follow_redirects=False)
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_redirect_deleted_url(client: AsyncClient, mock_redis, test_session):
    """
    Test redirect to a deleted (soft-deleted) URL.
    """
    # Setup: Create and then delete a short URL
    mock_redis.get.return_value = None
    create_response = await client.post(
        "/shorten",
        json={"url": "https://example.com/delete-test"}
    )
    short_id = create_response.json()["short_id"]
    
    # Delete the URL
    await client.delete(f"/{short_id}")
    
    # Mock Redis to return None (cache cleared on delete)
    mock_redis.get.return_value = None
    
    # Try to redirect
    response = await client.get(f"/{short_id}", follow_redirects=False)
    
    assert response.status_code == 404