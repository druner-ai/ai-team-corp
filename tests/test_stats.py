import pytest


@pytest.mark.asyncio
async def test_stats(client):
    # Create short URL
    response = client.post("/shorten", json={"url": "https://example.com"})
    short_code = response.json()["short_code"]
    # Access it to generate a click
    client.get(f"/{short_code}", follow_redirects=False)
    # Get stats
    response = client.get(f"/{short_code}/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["clicks"] == 1
    assert data["original_url"] == "https://example.com"
