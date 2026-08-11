"""
Repository for URL and click database operations.

Contains all SQL queries for the urls and clicks tables.
"""

import logging
from typing import Optional, Dict, Any, List

import aiosqlite

from app.repositories.database import DatabaseManager

logger = logging.getLogger(__name__)


class URLRepository:
    """
    Repository for URL and click data access.

    Encapsulates all SQL queries, using parameterized statements
    to prevent SQL injection.
    """

    def __init__(self, db_manager: DatabaseManager) -> None:
        """
        Initialize the repository.

        Args:
            db_manager: DatabaseManager instance for connection management.
        """
        self._db_manager = db_manager

    async def insert_url(self, url_data: Dict[str, Any]) -> int:
        """
        Insert a new URL record.

        Args:
            url_data: Dictionary with keys: short_code, original_url, created_at,
                      expires_at, is_active.

        Returns:
            The ID of the newly inserted row.
        """
        async with self._db_manager.get_connection() as conn:
            cursor = await conn.execute(
                """
                INSERT INTO urls (short_code, original_url, created_at, expires_at, is_active)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    url_data["short_code"],
                    url_data["original_url"],
                    url_data["created_at"],
                    url_data.get("expires_at"),
                    url_data.get("is_active", 1),
                ),
            )
            await conn.commit()
            return cursor.lastrowid

    async def get_by_code(self, short_code: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a URL record by its short code.

        Args:
            short_code: The short code to look up.

        Returns:
            Dictionary with URL data, or None if not found.
        """
        async with self._db_manager.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT * FROM urls WHERE short_code = ?",
                (short_code,),
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return dict(row)

    async def deactivate(self, url_id: int) -> None:
        """
        Deactivate a URL by setting is_active to 0.

        Args:
            url_id: The ID of the URL to deactivate.
        """
        async with self._db_manager.get_connection() as conn:
            await conn.execute(
                "UPDATE urls SET is_active = 0, updated_at = datetime('now') WHERE id = ?",
                (url_id,),
            )
            await conn.commit()

    async def insert_click(self, click_data: Dict[str, Any]) -> int:
        """
        Insert a new click record.

        Args:
            click_data: Dictionary with keys: url_id, clicked_at, ip_address,
                        user_agent, referer.

        Returns:
            The ID of the newly inserted row.
        """
        async with self._db_manager.get_connection() as conn:
            cursor = await conn.execute(
                """
                INSERT INTO clicks (url_id, clicked_at, ip_address, user_agent, referer)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    click_data["url_id"],
                    click_data["clicked_at"],
                    click_data.get("ip_address"),
                    click_data.get("user_agent"),
                    click_data.get("referer"),
                ),
            )
            await conn.commit()
            return cursor.lastrowid

    async def get_stats(self, url_id: int) -> Optional[Dict[str, Any]]:
        """
        Get aggregate click statistics for a URL.

        Args:
            url_id: The ID of the URL.

        Returns:
            Dictionary with clicks_count and last_click_at, or None.
        """
        async with self._db_manager.get_connection() as conn:
            cursor = await conn.execute(
                """
                SELECT
                    COUNT(*) as clicks_count,
                    MAX(clicked_at) as last_click_at
                FROM clicks
                WHERE url_id = ?
                """,
                (url_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return dict(row)

    async def get_recent_clicks(self, url_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get the most recent click records for a URL.

        Args:
            url_id: The ID of the URL.
            limit: Maximum number of records to return.

        Returns:
            List of click dictionaries, ordered by clicked_at descending.
        """
        async with self._db_manager.get_connection() as conn:
            cursor = await conn.execute(
                """
                SELECT clicked_at, ip_address, user_agent, referer
                FROM clicks
                WHERE url_id = ?
                ORDER BY clicked_at DESC
                LIMIT ?
                """,
                (url_id, limit),
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
