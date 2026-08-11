"""
Tests for URL validation and SSRF protection.
"""
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_valid_url_accepted(client: AsyncClient):
    valid_urls = [
        "https://example.com",
        "http://test.co.uk/path?q=1",
        "https://sub.domain.com:8080/",
    ]
    for url in valid_urls:
        resp = await client.post("/shorten/", json={"url": url})
        assert resp.status_code == 201, f"Failed for {url}"

@pytest.mark.asyncio
async def test_invalid_url_rejected(client: AsyncClient):
    invalid_urls = [
        "not_a_url",
        "ftp://invalid-scheme.com",
        "htp://example.com",
        "localhost",
    ]
    for url in invalid_urls:
        resp = await client.post("/shorten/", json={"url": url})
        assert resp.status_code == 422, f"Should fail for {url}"

@pytest.mark.asyncio
async def test_ssrf_localhost_blocked(client: AsyncClient):
    blocked = [
        "http://localhost/admin",
        "http://127.0.0.1:9000",
        "http://10.0.0.1/api",
        "http://[::1]/",
    ]
    for url in blocked:
        resp = await client.post("/shorten/", json={"url": url})
        assert resp.status_code == 422, f"Should block {url}"