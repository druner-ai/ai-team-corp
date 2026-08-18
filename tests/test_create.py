import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta

@pytest.mark.asyncio
async def test_create_url_success(client: AsyncClient):
    payload = {"url": "https://example.com"}
    response = await client.post("/shorten", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "short_code" in data
    assert data["url"] == "https://example.com"
    assert data["short_url"].endswith(data["short_code"])
    assert data["clicks"] == 0

@pytest.mark.asyncio
async def test_create_url_with_custom_code(client: AsyncClient):
    payload = {"url": "https://example.com", "custom_code": "mycode"}
    response = await client.post("/shorten", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["short_code"] == "mycode"

@pytest.mark.asyncio
async def test_create_url_duplicate_custom_code(client: AsyncClient):
    payload = {"url": "https://example.com", "custom_code": "dupcode"}
    response1 = await client.post("/shorten", json=payload)
    assert response1.status_code == 201
    response2 = await client.post("/shorten", json=payload)
    assert response2.status_code == 409

@pytest.mark.asyncio
async def test_create_url_with_expires_at(client: AsyncClient):
    future = (datetime.utcnow() + timedelta(days=1)).isoformat()
    payload = {"url": "https://example.com", "expires_at": future}
    response = await client.post("/shorten", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "expires_at" in data
    assert data["expires_at"] is not None
