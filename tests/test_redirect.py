import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_redirect_success(client: AsyncClient):
    # Create a short URL first
    create_resp = await client.post(
        "/api/v1/shorten", json={"url": "https://example.com/redirect-target"}
    )
    assert create_resp.status_code == 201
    code = create_resp.json()["code"]

    # Follow the redirect (disable auto redirect)
    response = await client.get(f"/{code}", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com/redirect-target"


@pytest.mark.anyio
async def test_redirect_not_found(client: AsyncClient):
    response = await client.get("/nonexistent", follow_redirects=False)
    assert response.status_code == 404


@pytest.mark.anyio
async def test_redirect_expired(client: AsyncClient):
    from datetime import datetime, timezone, timedelta

    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    # Create a short URL with expiration in the past
    create_resp = await client.post(
        "/api/v1/shorten",
        json={
            "url": "https://example.com/expired",
            "expires_at": past,
        },
    )
    assert create_resp.status_code == 201
    code = create_resp.json()["code"]

    response = await client.get(f"/{code}", follow_redirects=False)
    assert response.status_code == 410
