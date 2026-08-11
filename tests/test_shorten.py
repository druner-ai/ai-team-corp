import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta

@pytest.mark.asyncio
async def test_create_short_url(client: AsyncClient):
    payload = {"url": "https://example.org"}
    response = await client.post("/shorten", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["url"] == "https://example.org"
    assert len(data["short_code"]) == 6

@pytest.mark.asyncio
async def test_create_with_custom_code(client: AsyncClient):
    payload = {"url": "https://example.org", "custom_code": "cust1"}
    response = await client.post("/shorten", json=payload)
    assert response.status_code == 201
    assert response.json()["short_code"] == "cust1"

@pytest.mark.asyncio
async def test_create_duplicate_custom_code(client: AsyncClient):
    payload = {"url": "https://example.org", "custom_code": "dup2"}
    await client.post("/shorten", json=payload)
    response = await client.post("/shorten", json=payload)
    assert response.status_code == 409

@pytest.mark.asyncio
async def test_create_with_expires_at(client: AsyncClient):
    future = (datetime.utcnow() + timedelta(hours=1)).isoformat()
    payload = {"url": "https://example.org", "expires_at": future}
    response = await client.post("/shorten", json=payload)
    assert response.status_code == 201
    assert response.json()["expires_at"] is not None

@pytest.mark.asyncio
async def test_delete_existing_short_code(client: AsyncClient):
    # Create first
    create_resp = await client.post("/shorten", json={"url": "https://delete.me"})
    assert create_resp.status_code == 201
    short_code = create_resp.json()["short_code"]
    # Delete
    delete_resp = await client.delete(f"/{short_code}")
    assert delete_resp.status_code == 204
    # Verify gone
    get_resp = await client.get(f"/{short_code}")
    assert get_resp.status_code == 404
