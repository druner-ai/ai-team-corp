import pytest
import aiosqlite
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import get_db


@pytest.fixture
async def test_db():
    """Создаёт in-memory БД и инициализирует таблицы."""
    db = await aiosqlite.connect(":memory:")
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            short_code TEXT UNIQUE NOT NULL,
            original_url TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS clicks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            short_code TEXT NOT NULL,
            clicked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            referer TEXT,
            user_agent TEXT,
            FOREIGN KEY (short_code) REFERENCES urls(short_code)
        )
        """
    )
    await db.commit()
    yield db
    await db.close()


@pytest.fixture
async def client(test_db):
    """Переопределяет зависимость get_db на тестовую БД."""
    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
