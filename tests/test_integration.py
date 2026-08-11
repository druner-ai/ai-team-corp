"""End-to-end integration scenarios."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_full_lifecycle(client: AsyncClient):
    """
    System MUST support: create → redirect → stats → delete → redirect fails.
    """
    # 1. Create
    create_resp = await client.post("/api/shorten", json={"url": "https://example.com"})
    assert create_resp.status_code == 201
    short_code = create_resp.json()["short_code"]

    # 2. Redirect
    redir_resp = await client.get(f"/{short_code}", follow_redirects=False)
    assert redir_resp.status_code == 302
    assert redir_resp.headers["location"] == "https://example.com"

    # 3. Stats
    stats_resp = await client.get(f"/api/stats/{short_code}")
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["total_clicks"] == 1

    # 4. Delete
    del_resp = await client.delete(f"/api/shorten/{short_code}")
    assert del_resp.status_code == 204

    # 5. Redirect after delete must fail
    redir2_resp = await client.get(f"/{short_code}", follow_redirects=False)
    assert redir2_resp.status_code in (404, 410)

    # 6. Stats after delete – may return 404 (link not found)
    stats2_resp = await client.get(f"/api/stats/{short_code}")
    # Architecture says stats returns 404 if not found; after soft delete it's inactive, so 404
    assert stats2_resp.status_code == 404


@pytest.mark.asyncio
async def test_multiple_redirects_accumulate_clicks(client: AsyncClient):
    """System MUST count every redirect."""
    create_resp = await client.post("/api/shorten", json={"url": "https://example.com"})
    short_code = create_resp.json()["short_code"]

    for _ in range(3):
        await client.get(f"/{short_code}", follow_redirects=False)

    stats_resp = await client.get(f"/api/stats/{short_code}")
    assert stats_resp.status_code == 200
    assert stats_resp.json()["total_clicks"] == 3


@pytest.mark.asyncio
async def test_custom_code_and_redirect(client: AsyncClient):
    """System MUST work with custom codes."""
    payload = {"url": "https://example.com", "custom_code": "mycode"}
    create_resp = await client.post("/api/shorten", json=payload)
    assert create_resp.status_code == 201
    assert create_resp.json()["short_code"] == "mycode"

    redir_resp = await client.get("/mycode", follow_redirects=False)
    assert redir_resp.status_code == 302
    assert redir_resp.headers["location"] == "https://example.com"
