"""
Модуль для работы с базой данных SQLite через aiosqlite.

Предоставляет:
- init_db() — инициализация таблиц
- get_db() — асинхронный генератор соединений (Dependency Injection)
"""

import os
from typing import AsyncGenerator

import aiosqlite

from app.config import settings


async def init_db() -> None:
    """
    Инициализация базы данных.
    Создаёт таблицы urls и clicks, если они ещё не существуют.
    """
    # Убедимся, что директория для БД существует
    db_dir = os.path.dirname(settings.database_url.replace("sqlite:///", ""))
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    async with aiosqlite.connect(settings.database_url.replace("sqlite:///", "")) as db:
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


async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """
    Асинхронный генератор соединений с БД.
    Используется как зависимость в FastAPI (Depends).
    Гарантирует закрытие соединения после обработки запроса.
    """
    db_path = settings.database_url.replace("sqlite:///", "")
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        yield db
