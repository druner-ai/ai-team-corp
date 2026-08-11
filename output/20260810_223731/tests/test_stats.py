"""
Tests for GET /stats/{id}.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.url import URLRecord


@pytest.mark.asyncio
async def test_stats_existing(async_client: AsyncClient, db_session: AsyncSession):
    record = URLRecord(id="stat123", original_url="https://example.com/stat", clicks=42)
    db_session.add(record)
    await db_session.commit()

    response = await async_client.get("/stats/stat123")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "stat123"
    assert data["original_url"] == "https://example.com/stat"
    assert data["clicks"] == 42
    assert "created_at" in data


@pytest.mark.asyncio
async def test_stats_not_found(async_client: AsyncClient):
    response = await async_client.get("/stats/nonexist")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_stats_deleted(async_client: AsyncClient, db_session: AsyncSession):
    record = URLRecord(id="deleted", original_url="https://example.com/deleted", deleted=True)
    db_session.add(record)
    await db_session.commit()

    response = await async_client.get("/stats/deleted")
    # Should return 404 because stats service filters out deleted
    assert response.status_code == 404