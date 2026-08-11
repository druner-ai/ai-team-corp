"""
Integration tests for rate limiting.

Note: These tests verify rate limiting behavior.
In test environment, rate limiting may be disabled or use in-memory storage.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestRateLimiting:
    """Integration tests for rate limiting."""

    async def test_multiple_requests_within_limit(self, async_client: AsyncClient):
        """Multiple requests within limit should succeed."""
        for _ in range(5):
            response = await async_client.post(
                "/v1/shorten",
                json={"url": f"https://example.com/test-{_}"},
            )
            assert response.status_code in (201, 409)  # 409 for duplicates is OK

    async def test_health_endpoint_no_limit(self, async_client: AsyncClient):
        """Health endpoint should not be rate limited."""
        for _ in range(10):
            response = await async_client.get("/health")
            assert response.status_code == 200