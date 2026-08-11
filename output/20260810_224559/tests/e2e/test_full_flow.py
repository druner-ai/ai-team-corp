"""
End-to-end test simulating the full user flow.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_full_flow(client: AsyncClient):
    """Create, redirect, check stats, delete, verify 404."""
    # Step 1: Shorten
    resp = await client.post("/v1/shorten", json={"url": "https://example.com/fullflow"})
    assert resp.status_code == 201
    data = resp.json()
    short_id = data["short_id"]
    short_url = data["short_url"]

    # Step 2: Redirect (twice)
    for _ in range(2):
        redir = await client.get(f"/v1/{short_id}", follow_redirects=False)
        assert redir.status_code == 302
        assert redir.headers["location"] == "https://example.com/fullflow"

    # Step 3: Force flush counters (since flusher is background, we flush manually)
    from src.services.stats_service import StatsService
    from src.repositories.url_repository import UrlRepository
    from src.core.redis_client import redis_client
    from src.core.database import async_session_factory
    async with async_session_factory() as session:
        repo = UrlRepository(session)
        stats_svc = StatsService(redis_client)
        await stats_svc.flush_counters(repo)
        await session.commit()

    # Step 4: Check stats
    stats_resp = await client.get(f"/v1/stats/{short_id}")
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["click_count"] == 2

    # Step 5: Delete
    del_resp = await client.delete(f"/v1/{short_id}")
    assert del_resp.status_code == 204

    # Step 6: Redirect after delete returns 404
    redir2 = await client.get(f"/v1/{short_id}")
    assert redir2.status_code == 404

    # Step 7: Stats after delete
    stats2 = await client.get(f"/v1/stats/{short_id}")
    assert stats2.status_code == 404