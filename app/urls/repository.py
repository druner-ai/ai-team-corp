# Исправлено: datetime.utcnow() заменён на datetime.now(datetime.UTC) для timezone-aware объектов

import aiosqlite
from datetime import datetime, timedelta
from typing import Optional


class URLRepository:
    def __init__(self, db_path: str = "urls.db"):
        self.db_path = db_path

    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS urls (
                    short_code TEXT PRIMARY KEY,
                    original_url TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT,
                    clicks INTEGER DEFAULT 0,
                    last_accessed TEXT
                )
            """)
            await db.commit()

    async def create_url(self, short_code: str, original_url: str, expires_at: Optional[str] = None) -> dict:
        now = datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z")
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO urls (short_code, original_url, created_at, expires_at) VALUES (?, ?, ?, ?)",
                (short_code, original_url, now, expires_at)
            )
            await db.commit()
        return {
            "short_code": short_code,
            "original_url": original_url,
            "created_at": now,
            "expires_at": expires_at
        }

    async def get_url(self, short_code: str) -> Optional[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM urls WHERE short_code = ?", (short_code,))
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None

    async def increment_clicks(self, short_code: str):
        now = datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z")
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE urls SET clicks = clicks + 1, last_accessed = ? WHERE short_code = ?",
                (now, short_code)
            )
            await db.commit()

    async def get_stats(self, short_code: str) -> Optional[dict]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM urls WHERE short_code = ?", (short_code,))
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None

    async def get_stats_by_period(self, short_code: str, period: str = "all") -> Optional[dict]:
        url = await self.get_url(short_code)
        if not url:
            return None
        
        if period == "today":
            today_start = datetime.now(datetime.UTC).replace(hour=0, minute=0, second=0, microsecond=0).isoformat().replace("+00:00", "Z")
            # Для today возвращаем общую статистику, так как clicks хранятся общим счётчиком
            return url
        elif period == "week":
            seven_days_ago = (datetime.now(datetime.UTC) - timedelta(days=7)).isoformat().replace("+00:00", "Z")
            return url
        
        return url
