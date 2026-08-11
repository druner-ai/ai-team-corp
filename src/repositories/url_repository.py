"""
Repository layer for URL database operations.

Encapsulates all raw SQL queries for the urls table.
All queries use parameterized statements to prevent SQL injection.
"""

import logging
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)


class URLRepository:
    """
    Repository for URL-related database operations.

    Provides methods for inserting, retrieving, and updating URL records
    using parameterized SQL queries.
    """

    def __init__(self, db: aiosqlite.Connection) -> None:
        """
        Initialize the repository with a database connection.

        Args:
            db: An active aiosqlite database connection.
        """
        self._db = db

    async def insert(self, short_code: str, original_url: str) -> None:
        """
        Insert a new short URL record.

        Args:
            short_code: The generated short code.
            original_url: The original URL to associate with the code.

        Raises:
            aiosqlite.IntegrityError: If the short_code already exists (unique constraint).
        """
        await self._db.execute(
            "INSERT INTO urls (short_code, original_url) VALUES (?, ?)",
            (short_code, original_url),
        )
        await self._db.commit()

    async def get_by_code(self, short_code: str) -> dict[str, Any] | None:
        """
        Retrieve a URL record by its short code.

        Args:
            short_code: The short code to look up.

        Returns:
            A dict with the record fields if found, None otherwise.
        """
        cursor = await self._db.execute(
            "SELECT short_code, original_url, created_at, clicks FROM urls WHERE short_code = ?",
            (short_code,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    async def increment_clicks(self, short_code: str) -> None:
        """
        Atomically increment the click counter for a short code.

        Uses a single UPDATE statement to avoid race conditions.

        Args:
            short_code: The short code whose click count to increment.
        """
        await self._db.execute(
            "UPDATE urls SET clicks = clicks + 1 WHERE short_code = ?",
            (short_code,),
        )
        await self._db.commit()
