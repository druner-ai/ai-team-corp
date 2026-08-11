"""
Integration tests for DELETE /{short_code} endpoint.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestDeleteEndpoint:
    """Integration tests for URL deletion."""

    async def test_delete_existing_url(self, async_client: AsyncClient):
        """Should successfully delete an existing URL."""
        # Create URL
        create_response = await async_client.post(
            "/v1/shorten",
            json={"url": "https://example.com/delete-me"},
        )
        short_code = create_response.json()["short_code"]

        # Delete it
        response = await async_client.delete(f"/v1/{short_code}")

        assert response.status_code == 204

    async def test_delete_nonexistent_code(self, async_client: AsyncClient):
        """Should return 404 for non-existent short code."""
        response = await async_client.delete("/v1/nonexistent")

        assert response.status_code == 404

    async def test_delete_already_deleted(self, async_client: AsyncClient):
        """Should return 409 for already deleted URL."""
        # Create and delete
        create_response = await async_client.post(
            "/v1/shorten",
            json={"url": "https://example.com/double-delete"},
        )
        short_code = create_response.json()["short_code"]
        await async_client.delete(f"/v1/{short_code}")

        # Try to delete again
        response = await async_client.delete(f"/v1/{short_code}")

        assert response.status_code == 409

    async def test_delete_makes_url_inaccessible(self, async_client: AsyncClient):
        """Deleted URL should not be accessible."""
        # Create URL
        create_response = await async_client.post(
            "/v1/shorten",
            json={"url": "https://example.com/gone"},
        )
        short_code = create_response.json()["short_code"]

        # Delete it
        await async_client.delete(f"/v1/{short_code}")

        # Try to access
        response = await async_client.get(f"/v1/{short_code}")

        assert response.status_code == 404