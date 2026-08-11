import aiosqlite
from contextlib import asynccontextmanager

DATABASE_URL = "url_shortener.db"


async def get_db():
    """Асинхронный генератор соединения с БД."""
    db = await aiosqlite.connect(DATABASE_URL)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()


async def init_db():
    """Создание таблиц, если их нет."""
    async with aiosqlite.connect(DATABASE_URL) as db:
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
