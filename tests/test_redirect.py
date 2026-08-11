import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_redirect_success(client: AsyncClient):
    # Create a short link
    create_resp = await client.post("/api/v1/shorten", json={"url": "https://example.com"})
    assert create_resp.status_code == 201
    short_code = create_resp.json()["short_code"]

    # Access it
    redirect_resp = await client.get(f"/{short_code}", follow_redirects=False)
    assert redirect_resp.status_code == 302
    assert redirect_resp.headers["location"] == "https://example.com"


@pytest.mark.asyncio
async def test_redirect_not_found(client: AsyncClient):
    response = await client.get("/nonexistent")
    assert response.status_code == 404
    assert response.json()["detail"] == "Short link not found"


@pytest.mark.asyncio
async def test_redirect_deactivated(client: AsyncClient):
    # Insert a deactivated link directly
    from app.database import get_db
    db = await get_db()
    await db.execute("INSERT INTO urls (short_code, original_url, is_active) VALUES (?, ?, 0)",
                     ("deact1", "https://example.com"))
    await db.commit()
    response = await client.get("/deact1")
    assert response.status_code == 410
    assert response.json()["detail"] == "Short link is deactivated"
