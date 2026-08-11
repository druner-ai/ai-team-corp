"""
Integration tests for POST /shorten endpoint.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestShortenEndpoint:
    """Integration tests for URL shortening."""

    async def test_shorten_valid_url(self, async_client: AsyncClient):
        """Should successfully shorten a valid URL."""
        response = await async_client.post(
            "/v1/shorten",
            json={"url": "https://example.com/very/long/path"},
        )

        assert response.status_code == 201
        data = response.json()
        assert "short_code" in data
        assert "short_url" in data
        assert "original_url" in data
        assert data["original_url"] == "https://example.com/very/long/path"
        assert len(data["short_code"]) == 6

    async def test_shorten_duplicate_url(self, async_client: AsyncClient):
        """Should return 409 for duplicate URL."""
        # First request
        await async_client.post(
            "/v1/shorten",
            json={"url": "https://example.com/unique"},
        )

        # Second request with same URL
        response = await async_client.post(
            "/v1/shorten",
            json={"url": "https://example.com/unique"},
        )

        assert response.status_code == 409
        data = response.json()
        assert "already shortened" in data["detail"].lower()

    async def test_shorten_invalid_url(self, async_client: AsyncClient):
        """Should return 400 for invalid URL."""
        response = await async_client.post(
            "/v1/shorten",
            json={"url": "not-a-valid-url"},
        )

        assert response.status_code == 400

    async def test_shorten_missing_url_field(self, async_client: AsyncClient):
        """Should return 422 for missing url field."""
        response = await async_client.post(
            "/v1/shorten",
            json={},
        )

        assert response.status_code == 422

    async def test_shorten_empty_url(self, async_client: AsyncClient):
        """Should return 400 for empty URL."""
        response = await async_client.post(
            "/v1/shorten",
            json={"url": ""},
        )

        assert response.status_code == 400

    async def test_shorten_url_with_special_chars(self, async_client: AsyncClient):
        """Should handle URLs with special characters."""
        response = await async_client.post(
            "/v1/shorten",
            json={"url": "https://example.com/path?key=value&foo=bar%20baz"},
        )

        assert response.status_code == 201
        data = response.json()
        assert "key=value" in data["original_url"]