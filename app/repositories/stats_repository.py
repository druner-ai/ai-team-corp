import aiosqlite
from typing import List


class StatsRepository:
    """Handles raw SQL queries against the `clicks` table."""

    async def record_click(
        self,
        conn: aiosqlite.Connection,
        url_id: int,
        clicked_at: str,
        ip_address: str | None,
        user_agent: str | None,
        referer: str | None,
    ) -> None:
        """Insert a new click record."""
        await conn.execute(
            "INSERT INTO clicks (url_id, clicked_at, ip_address, user_agent, referer) VALUES (?, ?, ?, ?, ?);",
            (url_id, clicked_at, ip_address, user_agent, referer),
        )
        await conn.commit()

    async def get_total_clicks(self, conn: aiosqlite.Connection, url_id: int) -> int:
        """Return total number of clicks for a given URL."""
        async with conn.execute(
            "SELECT COUNT(*) FROM clicks WHERE url_id = ?;", (url_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def get_recent_clicks(
        self, conn: aiosqlite.Connection, url_id: int, limit: int
    ) -> List[dict]:
        """Return the most recent clicks (up to `limit`)."""
        clicks = []
        async with conn.execute(
            "SELECT clicked_at, ip_address, user_agent FROM clicks WHERE url_id = ? ORDER BY clicked_at DESC LIMIT ?;",
            (url_id, limit),
        ) as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                clicks.append(
                    {
                        "clicked_at": row[0],
                        "ip_address": row[1],
                        "user_agent": row[2],
                    }
                )
        return clicks
