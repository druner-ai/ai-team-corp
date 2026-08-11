import aiosqlite
from app.config import settings
import logging

logger = logging.getLogger(__name__)

_db: aiosqlite.Connection | None = None


async def init_db() -> None:
    """Создаёт и настраивает подключение к SQLite, выполняет миграции."""
    global _db
    logger.info("Initializing database...")
    _db = await aiosqlite.connect(settings.database_path)
    await _db.execute("PRAGMA journal_mode=WAL")
    await _db.execute("PRAGMA synchronous=NORMAL")
    await _db.execute("PRAGMA mmap_size=268435456")
    await _db.execute("PRAGMA foreign_keys=ON")
    # Создание таблиц
    await _db.executescript("""
        CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            short_code TEXT NOT NULL UNIQUE,
            original_url TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            expires_at TEXT,
            is_active INTEGER NOT NULL DEFAULT 1
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_urls_short_code ON urls(short_code);
        CREATE INDEX IF NOT EXISTS idx_urls_created_at ON urls(created_at);

        CREATE TABLE IF NOT EXISTS clicks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url_id INTEGER NOT NULL,
            clicked_at TEXT NOT NULL DEFAULT (datetime('now')),
            ip TEXT,
            user_agent TEXT,
            referer TEXT,
            FOREIGN KEY (url_id) REFERENCES urls(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_clicks_url_id ON clicks(url_id);
        CREATE INDEX IF NOT EXISTS idx_clicks_clicked_at ON clicks(clicked_at);
    """)
    await _db.commit()
    logger.info("Database initialized")


async def get_db() -> aiosqlite.Connection:
    """Возвращает текущее соединение с БД (должно быть предварительно инициализировано)."""
    assert _db is not None, "Database not initialized"
    return _db


async def close_db() -> None:
    """Закрывает соединение с БД."""
    global _db
    if _db:
        await _db.close()
        _db = None
        logger.info("Database connection closed")
