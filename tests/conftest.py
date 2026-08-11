"""
Фикстуры для тестов.
Используем in-memory SQLite для изоляции тестов.
"""
import pytest
import aiosqlite
from fastapi.testclient import TestClient
from src.app.main import app
from src.app.database import get_db, init_db


@pytest.fixture
async def test_db():
    """Создаёт in-memory БД и инициализирует таблицы."""
    db = await aiosqlite.connect(":memory:")
    db.row_factory = aiosqlite.Row
    # Инициализация схемы
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("""
        CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            short_code TEXT UNIQUE NOT NULL,
            original_url TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS clicks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            short_code TEXT NOT NULL,
            clicked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            referer TEXT,
            user_agent TEXT,
            FOREIGN KEY (short_code) REFERENCES urls(short_code)
        )
    """)
    await db.commit()
    yield db
    await db.close()


@pytest.fixture
async def client(test_db):
    """Переопределяем зависимость get_db на тестовую БД."""
    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
