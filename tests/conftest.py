"""
Фикстуры для тестов.

Исправление: добавлена фикстура test_db_path, которая создаёт временную БД
для каждого теста, инициализирует таблицы и очищает после завершения.
Причина: тесты должны работать с изолированной БД, а не с production-файлом.
"""

import os
import tempfile
from typing import AsyncGenerator

import aiosqlite
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.database import get_db
from app.main import app


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """Указываем бэкенд для pytest-asyncio."""
    return "asyncio"


@pytest_asyncio.fixture
async def test_db_path() -> AsyncGenerator[str, None]:
    """
    Создаёт временный файл БД для тестов.
    Инициализирует таблицы и возвращает путь.
    После теста файл удаляется.
    """
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    # Инициализируем таблицы
    async with aiosqlite.connect(path) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS urls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                short_code TEXT NOT NULL UNIQUE,
                original_url TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed_at TIMESTAMP,
                access_count INTEGER DEFAULT 0
            )
        """)
        await db.commit()

    yield path

    # Очистка
    if os.path.exists(path):
        os.remove(path)


@pytest_asyncio.fixture
async def test_db(test_db_path: str) -> AsyncGenerator[aiosqlite.Connection, None]:
    """
    Предоставляет соединение с тестовой БД.
    Используется для прямых запросов в тестах.
    """
    async with aiosqlite.connect(test_db_path) as db:
        db.row_factory = aiosqlite.Row
        yield db


@pytest_asyncio.fixture
async def client(test_db_path: str) -> AsyncGenerator[AsyncClient, None]:
    """
    Создаёт тестовый HTTP-клиент с переопределённой зависимостью БД.
    Все запросы будут использовать временную тестовую БД.
    """

    async def override_get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
        async with aiosqlite.connect(test_db_path) as db:
            db.row_factory = aiosqlite.Row
            yield db

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
