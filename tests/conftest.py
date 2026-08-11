import asyncio
from pathlib import Path

import aiosqlite
import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from src.app.database import get_db
from src.app.routers import health, redirect, shorten, stats


@pytest.fixture(scope="function")
async def test_db():
    """Create an in‑memory SQLite database with the application schema."""
    conn = await aiosqlite.connect(":memory:")
    await conn.execute("PRAGMA foreign_keys = ON;")
    schema_path = Path(__file__).parent.parent / "src" / "app" / "schema.sql"
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    await conn.executescript(schema_sql)
    await conn.commit()
    yield conn
    await conn.close()


@pytest.fixture(scope="function")
async def test_app(test_db: aiosqlite.Connection) -> FastAPI:
    """Build a FastAPI app that uses the test database via dependency override."""
    app = FastAPI()
    app.include_router(health.router)
    app.include_router(shorten.router, prefix="/api/v1")
    app.include_router(stats.router, prefix="/api/v1")
    app.include_router(redirect.router)

    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    return app


@pytest.fixture(scope="function")
async def client(test_app: FastAPI) -> AsyncClient:
    """Provide an HTTP test client backed by the test application."""
    async with AsyncClient(app=test_app, base_url="http://test") as ac:
        yield ac
