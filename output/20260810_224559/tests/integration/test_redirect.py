"""
Integration tests for GET /{short_id} redirect.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_redirect_success(client: AsyncClient):
    """Should issue 302 redirect to original URL."""
    # First create a short URL
    create_resp = await client.post("/v1/shorten", json={"url": "https://example.org/target"})
    assert create_resp.status_code == 201
    short_id = create_resp.json()["short_id"]

    # Redirect
    redirect_resp = await client.get(f"/v1/{short_id}", follow_redirects=False)
    assert redirect_resp.status_code == 302
    assert redirect_resp.headers["location"] == "https://example.org/target"


@pytest.mark.asyncio
async def test_redirect_not_found(client: AsyncClient):
    """Should return 404 for non-existent short_id."""
    resp = await client.get("/v1/nonexist", follow_redirects=False)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_redirect_deleted(client: AsyncClient):
    """Should return 404 after deletion."""
    # Create
    resp = await client.post("/v1/shorten", json={"url": "https://example.org/deleteme"})
    short_id = resp.json()["short_id"]

    # Delete
    del_resp = await client.delete(f"/v1/{short_id}")
    assert del_resp.status_code == 204

    # Redirect now 404
    redir_resp = await client.get(f"/v1/{short_id}")
    assert redir_resp.status_code == 404