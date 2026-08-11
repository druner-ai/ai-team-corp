"""
Tests for DELETE /{id} endpoint.
"""
import pytest
from httpx import AsyncClient
from unittest.mock import patch


@pytest.mark.asyncio
async def test_delete_success(client: AsyncClient, mock_redis, test_session):
    """
    Test successful deletion of a short URL.
    """
    # Setup: Create a short URL
    mock_redis.get.return_value = None
    create_response = await client.post(
        "/shorten",
        json={"url": "https://example.com/delete-test"}
    )
    short_id = create_response.json()["short_id"]
    
    # Delete the URL
    response = await client.delete(f"/{short_id}")
    
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_not_found(client: AsyncClient, mock_redis):
    """
    Test deletion of non-existent short ID.
    """
    mock_redis.get.return_value = None
    
    response = await client.delete("/nonexist")
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_already_deleted(client: AsyncClient, mock_redis, test_session):
    """
    Test deletion of already deleted URL.
    """
    # Setup: Create and delete a short URL
    mock_redis.get.return_value = None
    create_response = await client.post(
        "/shorten",
        json={"url": "https://example.com/double-delete"}
    )
    short_id = create_response.json()["short_id"]
    
    # First delete
    await client.delete(f"/{short_id}")
    
    # Second delete should fail
    response = await client.delete(f"/{short_id}")
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_invalid_id(client: AsyncClient):
    """
    Test deletion with invalid short ID format.
    """
    response = await client.delete("/ab")
    
    assert response.status_code == 404