"""
Repository for URL-related database operations.
All queries are parameterized to prevent SQL injection.
"""
import aiosqlite
from typing import Optional


class UrlRepository:
    """Handles CRUD operations for the urls table."""

    @staticmethod
    async def insert_url(conn: aiosqlite.Connection, code: str, original_url: str) -> int:
        """
        Insert a new shortened URL and return its ID.
        """
        cursor = await conn.execute(
            "INSERT INTO urls (code, original_url) VALUES (?, ?)",
            (code, original_url),
        )
        await conn.commit()
        return cursor.lastrowid

    @staticmethod
    async def get_url_by_code(conn: aiosqlite.Connection, code: str) -> Optional[dict]:
        """
        Retrieve URL record by short code.
        Returns a dictionary with keys: id, code, original_url, created_at, or None.
        """
        cursor = await conn.execute(
            "SELECT id, code, original_url, created_at FROM urls WHERE code = ?",
            (code,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return {
            "id": row[0],
            "code": row[1],
            "original_url": row[2],
            "created_at": row[3],
        }
