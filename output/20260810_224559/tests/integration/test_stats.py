"""
Integration tests for GET /stats/{short_id} endpoint.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_stats_success(client: AsyncClient):
    """Should return statistics for a valid short_id."""
    # Create
    resp = await client.post("/v1/shorten", json={"url": "https://example.org/stats"})
    assert resp.status_code == 201
    short_id = resp.json()["short_id"]

    # Perform a few redirects to increase counters
    for _ in range(3):
        await client.get(f"/v1/{short_id}", follow_redirects=False)

    # Flush counters? In tests, background flusher is not running,
    # but we can manually flush or rely on the fact that the stats endpoint
    # reads from DB, and counters are in Redis. We need to trigger a flush.
    # For integration test simplicity, we can directly increment DB via the service
    # but that breaks the flow. Instead, we'll rely on the stats_flusher
    # but it's not started in test lifespan? The lifespan in main.py starts a flusher.
    # Our test client uses the real app, so lifespan runs. However, the flusher
    # runs on a 60-second interval, so unlikely to flush during test.
    # We'll directly call flush_counters from the test for immediate verification.
    from src.services.stats_service import StatsService
    from src.repositories.url_repository import UrlRepository
    from src.core.redis_client import redis_client
    from src.core.database import async_session_factory

    async with async_session_factory() as session:
        repo = UrlRepository(session)
        stats_svc = StatsService(redis_client)
        await stats_svc.flush_counters(repo)
        await session.commit()

    # Now fetch stats
    stats_resp = await client.get(f"/v1/stats/{short_id}")
    assert stats_resp.status_code == 200
    data = stats_resp.json()
    assert data["short_id"] == short_id
    assert data["original_url"] == "https://example.org/stats"
    assert data["click_count"] == 3
    assert data["last_clicked_at"] is not None


@pytest.mark.asyncio
async def test_stats_not_found(client: AsyncClient):
    """Should return 404 for unknown short_id."""
    resp = await client.get("/v1/stats/nonexist")
    assert resp.status_code == 404