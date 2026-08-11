import pytest


@pytest.mark.asyncio
async def test_redirect(client):
    # First create a short URL
    response = client.post("/shorten", json={"url": "https://example.com"})
    short_code = response.json()["short_code"]
    # Now redirect
    response = client.get(f"/{short_code}", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com"
