"""
Integration tests for GET /stats/{short_code} endpoint.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestStatsEndpoint:
    """Integration tests for URL statistics."""

    async def test_stats_existing_url(self, async_client: AsyncClient):
        """Should return stats for existing URL."""
        # Create a short URL
        create_response = await async_client.post(
            "/v1/shorten",
            json={"url": "https://example.com/stats-test"},
        )
        short_code = create_response.json()["short_code"]

        # Get stats
        response = await async_client.get(f"/v1/stats/{short_code}")

        assert response.status_code == 200
        data = response.json()
        assert data["short_code"] == short_code
        assert data["original_url"] == "https://example.com/stats-test"
        assert "clicks" in data
        assert "created_at" in data
        assert data["clicks"] >= 0

    async def test_stats_nonexistent_code(self, async_client: AsyncClient):
        """Should return 404 for non-existent short code."""
        response = await async_client.get("/v1/stats/nonexistent")

        assert response.status_code == 404

    async def test_stats_deleted_url(self, async_client: AsyncClient):
        """Should return 404 for deleted URL."""
        # Create and delete
        create_response = await async_client.post(
            "/v1/shorten",
            json={"url": "https://example.com/stats-deleted"},
        )
        short_code = create_response.json()["short_code"]
        await async_client.delete(f"/v1/{short_code}")

        # Try to get stats
        response = await async_client.get(f"/v1/stats/{short_code}")

        assert response.status_code == 404

    async def test_stats_with_clicks(self, async_client: AsyncClient):
        """Stats should reflect click count."""
        # Create URL
        create_response = await async_client.post(
            "/v1/shorten",
            json={"url": "https://example.com/clicks-stats"},
        )
        short_code = create_response.json()["short_code"]

        # Generate some clicks
        for _ in range(5):
            await async_client.get(f"/v1/{short_code}", follow_redirects=False)

        # Check stats
        response = await async_client.get(f"/v1/stats/{short_code}")
        data = response.json()

        assert data["clicks"] == 5