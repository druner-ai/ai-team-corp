"""
Integration tests for GET /{short_code} redirect endpoint.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestRedirectEndpoint:
    """Integration tests for URL redirection."""

    async def test_redirect_existing_url(self, async_client: AsyncClient):
        """Should redirect to original URL for valid short code."""
        # First, create a short URL
        create_response = await async_client.post(
            "/v1/shorten",
            json={"url": "https://example.com/target"},
        )
        short_code = create_response.json()["short_code"]

        # Then, access the short URL
        response = await async_client.get(
            f"/v1/{short_code}",
            follow_redirects=False,
        )

        assert response.status_code == 307
        assert response.headers["location"] == "https://example.com/target"

    async def test_redirect_nonexistent_code(self, async_client: AsyncClient):
        """Should return 404 for non-existent short code."""
        response = await async_client.get("/v1/nonexistent")

        assert response.status_code == 404

    async def test_redirect_deleted_url(self, async_client: AsyncClient):
        """Should return 404 for deleted URL."""
        # Create a short URL
        create_response = await async_client.post(
            "/v1/shorten",
            json={"url": "https://example.com/to-delete"},
        )
        short_code = create_response.json()["short_code"]

        # Delete it
        await async_client.delete(f"/v1/{short_code}")

        # Try to access
        response = await async_client.get(f"/v1/{short_code}")

        assert response.status_code == 404

    async def test_redirect_increments_counter(self, async_client: AsyncClient):
        """Should increment click counter on redirect."""
        # Create a short URL
        create_response = await async_client.post(
            "/v1/shorten",
            json={"url": "https://example.com/count-test"},
        )
        short_code = create_response.json()["short_code"]

        # Access it multiple times
        for _ in range(3):
            await async_client.get(f"/v1/{short_code}", follow_redirects=False)

        # Check stats
        stats_response = await async_client.get(f"/v1/stats/{short_code}")
        stats = stats_response.json()

        assert stats["clicks"] == 3