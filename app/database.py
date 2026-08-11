"""
Database module: async SQLite connection and table initialization.
"""
import aiosqlite

DATABASE_URL = "url_shortener.db"
_db = None


async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        _db = await aiosqlite.connect(DATABASE_URL)
        _db.row_factory = aiosqlite.Row
    return _db


async def init_db():
    db = await get_db()
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS urls (
            slug TEXT PRIMARY KEY,
            original_url TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS clicks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT NOT NULL,
            clicked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT,
            FOREIGN KEY (slug) REFERENCES urls(slug)
        )
        """
    )
    await db.commit()


async def close_db():
    global _db
    if _db:
        await _db.close()
        _db = None
