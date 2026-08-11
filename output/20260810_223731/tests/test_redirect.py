"""
Tests for GET /{id} redirection.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.url import URLRecord


async def create_test_record(db_session: AsyncSession, short_id: str, original_url: str):
    record = URLRecord(id=short_id, original_url=original_url)
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)
    return record


@pytest.mark.asyncio
async def test_redirect_existing(async_client: AsyncClient, db_session: AsyncSession):
    await create_test_record(db_session, "abcdefg", "https://example.com/page")
    response = await async_client.get("/abcdefg")
    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com/page"


@pytest.mark.asyncio
async def test_redirect_not_found(async_client: AsyncClient):
    response = await async_client.get("/nonexist")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_redirect_deleted(async_client: AsyncClient, db_session: AsyncSession):
    record = await create_test_record(db_session, "del1234", "https://example.com/deleted")
    record.deleted = True
    await db_session.commit()
    response = await async_client.get("/del1234")
    assert response.status_code == 404