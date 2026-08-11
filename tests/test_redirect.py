import pytest


@pytest.mark.asyncio
async def test_redirect_valid_code(client):
    # Create a short URL first
    create_resp = await client.post("/shorten", json={"url": "https://example.com"})
    short_code = create_resp.json()["short_code"]

    # Perform redirect request (follow redirects disabled)
    response = await client.get(f"/{short_code}", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "https://example.com"


@pytest.mark.asyncio
async def test_redirect_not_found(client):
    response = await client.get("/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_redirect_increments_click_count(client):
    # Create a short URL
    create_resp = await client.post("/shorten", json={"url": "https://example.com"})
    short_code = create_resp.json()["short_code"]

    # Perform two redirects
    await client.get(f"/{short_code}", follow_redirects=False)
    await client.get(f"/{short_code}", follow_redirects=False)

    # Check stats
    stats_resp = await client.get(f"/stats/{short_code}")
    assert stats_resp.status_code == 200
    assert stats_resp.json()["clicks"] == 2
