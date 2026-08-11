import pytest


@pytest.mark.asyncio
async def test_create_short_url_valid(client):
    response = await client.post("/shorten", json={"url": "https://example.com"})
    assert response.status_code == 201
    data = response.json()
    assert "short_code" in data
    assert "short_url" in data
    assert data["original_url"] == "https://example.com"
    assert len(data["short_code"]) == 6


@pytest.mark.asyncio
async def test_create_short_url_invalid_url(client):
    response = await client.post("/shorten", json={"url": "not-a-valid-url"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_short_url_missing_field(client):
    response = await client.post("/shorten", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_short_url_duplicate_yields_unique_codes(client):
    url_payload = {"url": "https://example.org"}
    r1 = await client.post("/shorten", json=url_payload)
    r2 = await client.post("/shorten", json=url_payload)
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["short_code"] != r2.json()["short_code"]
