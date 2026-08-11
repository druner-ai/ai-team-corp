import logging
from app.database import DatabaseManager

logger = logging.getLogger(__name__)


class StatsService:
    """Business logic for link statistics."""

    def __init__(self, db: DatabaseManager):
        self._db = db

    async def get_stats(self, short_code: str) -> dict | None:
        """Return stats dict for a short code or None if not found."""
        row = await self._db.fetchone(
            "SELECT short_code, original_url, clicks, created_at FROM links WHERE short_code = ?",
            (short_code,),
        )
        return dict(row) if row else None

    async def increment_clicks(self, short_code: str) -> None:
        """Increment the clicks counter for the given short code."""
        await self._db.execute(
            "UPDATE links SET clicks = clicks + 1 WHERE short_code = ?",
            (short_code,),
        )
        logger.debug(f"Incremented clicks for {short_code}")
