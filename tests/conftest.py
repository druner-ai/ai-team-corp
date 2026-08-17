"""Fixtures для FastAPI тестов сервиса валидации банковских реквизитов.

Сервис stateless — БД нет. Используем AsyncClient + ASGITransport.
"""

import pytest
from httpx import AsyncClient, ASGITransport


@pytest.fixture(scope="function")
async def client():
    """FastAPI test client."""
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac
