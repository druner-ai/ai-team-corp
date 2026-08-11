"""
Unit/Integration tests for service layer functions.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.url import URLRecord
from app.services.url_service import create_short_url, get_original_url, cache_url, invalidate_cache
from app.services.stats_service import get_stats, increment_clicks
from app.services.delete_service import soft_delete


@pytest.mark.asyncio
async def test_create_short_url(db_session: AsyncSession):
    original = "https://example.com/test"
    record = await create_short_url(db_session, original)
    assert len(record.id) == 7
    assert record.original_url == original
    assert record.clicks == 0
    assert record.deleted is False

    # Verify persistence
    fetched = await db_session.get(URLRecord, record.id)
    assert fetched is not None


@pytest.mark.asyncio
async def test_increment_clicks(db_session: AsyncSession):
    record = URLRecord(id="clicks1", original_url="https://example.com/clickme", clicks=0)
    db_session.add(record)
    await db_session.commit()

    await increment_clicks(db_session, "clicks1")

    await db_session.refresh(record)
    assert record.clicks == 1

    await increment_clicks(db_session, "clicks1")
    await db_session.refresh(record)
    assert record.clicks == 2


@pytest.mark.asyncio
async def test_soft_delete(db_session: AsyncSession):
    record = URLRecord(id="todel13", original_url="https://example.com/delete")
    db_session.add(record)
    await db_session.commit()

    result = await soft_delete(db_session, "todel13")
    assert result is True
    assert record.deleted is True

    result2 = await soft_delete(db_session, "todel13")  # already deleted
    assert result2 is False


@pytest.mark.asyncio
async def test_get_stats_ok(db_session: AsyncSession):
    record = URLRecord(id="statok", original_url="https://example.com/stat", clicks=5)
    db_session.add(record)
    await db_session.commit()

    stats = await get_stats(db_session, "statok")
    assert stats is not None
    assert stats.clicks == 5

    # Deleted record should not be returned
    record.deleted = True
    await db_session.commit()
    stats2 = await get_stats(db_session, "statok")
    assert stats2 is None