"""
Repository for click-related database operations.
"""
import aiosqlite
from typing import Optional


class ClickRepository:
    """Handles operations for the clicks table."""

    @staticmethod
    async def insert_click(
        conn: aiosqlite.Connection,
        url_id: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """
        Record a click event for a given URL.
        """
        await conn.execute(
            "INSERT INTO clicks (url_id, ip_address, user_agent) VALUES (?, ?, ?)",
            (url_id, ip_address, user_agent),
        )
        await conn.commit()

    @staticmethod
    async def count_clicks(conn: aiosqlite.Connection, url_id: int) -> int:
        """
        Return total number of clicks for a URL.
        """
        cursor = await conn.execute(
            "SELECT COUNT(*) FROM clicks WHERE url_id = ?",
            (url_id,),
        )
        row = await cursor.fetchone()
        return row[0] if row else 0

    @staticmethod
    async def get_recent_clicks(
        conn: aiosqlite.Connection,
        url_id: int,
        limit: int = 10,
    ) -> list[dict]:
        """
        Retrieve the most recent clicks for a URL.
        Returns list of dicts with keys: clicked_at, ip_address, user_agent.
        """
        cursor = await conn.execute(
            "SELECT clicked_at, ip_address, user_agent FROM clicks WHERE url_id = ? ORDER BY clicked_at DESC LIMIT ?",
            (url_id, limit),
        )
        rows = await cursor.fetchall()
        return [
            {
                "clicked_at": row[0],
                "ip_address": row[1],
                "user_agent": row[2],
            }
            for row in rows
        ]
