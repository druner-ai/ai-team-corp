"""
Модуль для работы с базой данных SQLite через aiosqlite.
Без ORM — все запросы на чистом SQL.
"""
import aiosqlite
from typing import AsyncGenerator

DATABASE_URL = "url_shortener.db"


async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """
    Асинхронный генератор соединения с БД.
    Используется как зависимость FastAPI.
    """
    db = await aiosqlite.connect(DATABASE_URL)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()


async def init_db() -> None:
    """
    Инициализация БД: создание таблиц, если их нет.
    """
    async with aiosqlite.connect(DATABASE_URL) as db:
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


async def create_short_url(db: aiosqlite.Connection, short_code: str, original_url: str) -> None:
    """Создание записи короткой ссылки."""
    await db.execute(
        "INSERT INTO urls (short_code, original_url) VALUES (?, ?)",
        (short_code, original_url)
    )
    await db.commit()


async def get_original_url(db: aiosqlite.Connection, short_code: str) -> str | None:
    """Получение оригинального URL по короткому коду."""
    cursor = await db.execute(
        "SELECT original_url FROM urls WHERE short_code = ?",
        (short_code,)
    )
    row = await cursor.fetchone()
    return row["original_url"] if row else None


async def record_click(db: aiosqlite.Connection, short_code: str, referer: str | None, user_agent: str | None) -> None:
    """Запись клика по короткой ссылке."""
    await db.execute(
        "INSERT INTO clicks (short_code, referer, user_agent) VALUES (?, ?, ?)",
        (short_code, referer, user_agent)
    )
    await db.commit()


async def get_stats(db: aiosqlite.Connection, short_code: str) -> dict | None:
    """
    Получение статистики по короткой ссылке:
    - количество переходов
    - дата создания
    - последний переход
    - топ рефереров
    - топ User-Agent
    """
    # Проверяем существование ссылки
    cursor = await db.execute(
        "SELECT short_code, original_url, created_at FROM urls WHERE short_code = ?",
        (short_code,)
    )
    url_row = await cursor.fetchone()
    if not url_row:
        return None

    # Количество переходов
    cursor = await db.execute(
        "SELECT COUNT(*) as count FROM clicks WHERE short_code = ?",
        (short_code,)
    )
    count_row = await cursor.fetchone()
    click_count = count_row["count"]

    # Последний переход
    cursor = await db.execute(
        "SELECT clicked_at FROM clicks WHERE short_code = ? ORDER BY clicked_at DESC LIMIT 1",
        (short_code,)
    )
    last_click_row = await cursor.fetchone()
    last_click = last_click_row["clicked_at"] if last_click_row else None

    # Топ рефереров (до 5)
    cursor = await db.execute(
        "SELECT referer, COUNT(*) as count FROM clicks WHERE short_code = ? AND referer IS NOT NULL GROUP BY referer ORDER BY count DESC LIMIT 5",
        (short_code,)
    )
    top_referers = [{"referer": row["referer"], "count": row["count"]} async for row in cursor]

    # Топ User-Agent (до 5)
    cursor = await db.execute(
        "SELECT user_agent, COUNT(*) as count FROM clicks WHERE short_code = ? AND user_agent IS NOT NULL GROUP BY user_agent ORDER BY count DESC LIMIT 5",
        (short_code,)
    )
    top_user_agents = [{"user_agent": row["user_agent"], "count": row["count"]} async for row in cursor]

    return {
        "short_code": url_row["short_code"],
        "original_url": url_row["original_url"],
        "created_at": url_row["created_at"],
        "click_count": click_count,
        "last_click": last_click,
        "top_referers": top_referers,
        "top_user_agents": top_user_agents,
    }
