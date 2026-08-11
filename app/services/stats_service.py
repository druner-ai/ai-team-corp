"""Business logic for click statistics."""

import aiosqlite

from app.db.repository import increment_clicks, get_stats_by_code


class StatsService:
    """Service for managing click counters and statistics."""

    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    async def increment_clicks(self, short_code: str) -> None:
        """Atomically increment the click counter for a short code."""
        await increment_clicks(self.db, short_code)

    async def get_stats(self, short_code: str) -> dict | None:
        """Retrieve statistics for a short code."""
        row = await get_stats_by_code(self.db, short_code)
        if row is None:
            return None
        return {
            "short_code": row["short_code"],
            "original_url": row["original_url"],
            "clicks": row["clicks"],
            "created_at": row["created_at"],
            "last_visited_at": row["last_visited_at"],
        }
