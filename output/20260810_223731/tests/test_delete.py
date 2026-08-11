"""
Tests for DELETE /{id}.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.url import URLRecord


@pytest.mark.asyncio
async def test_delete_existing(async_client: AsyncClient, db_session: AsyncSession):
    record = URLRecord(id="todel12", original_url="https://example.com/todelete")
    db_session.add(record)
    await db_session.commit()

    response = await async_client.delete("/todel12")
    assert response.status_code == 204

    # Verify it's now deleted
    from sqlalchemy import select
    result = await db_session.execute(select(URLRecord).where(URLRecord.id == "todel12"))
    updated = result.scalar_one()
    assert updated.deleted is True

    # Redis cache should be invalidated (redirect fails)
    redirect_resp = await async_client.get("/todel12")
    assert redirect_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent(async_client: AsyncClient):
    response = await async_client.delete("/noidhere")
    assert response.status_code == 404