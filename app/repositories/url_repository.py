import aiosqlite
from typing import Optional


class UrlRepository:
    """Handles raw SQL queries against the `urls` table."""

    async def get_by_slug(self, conn: aiosqlite.Connection, slug: str) -> Optional[dict]:
        """Fetch a URL record (including inactive ones) by slug."""
        async with conn.execute(
            "SELECT id, slug, original_url, created_at, expires_at, is_active FROM urls WHERE slug = ?;",
            (slug,),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "slug": row[1],
                    "original_url": row[2],
                    "created_at": row[3],
                    "expires_at": row[4],
                    "is_active": row[5],
                }
            return None

    async def get_active_by_slug(self, conn: aiosqlite.Connection, slug: str) -> Optional[dict]:
        """Fetch an active URL record by slug (is_active = 1)."""
        async with conn.execute(
            "SELECT id, slug, original_url, created_at, expires_at, is_active FROM urls WHERE slug = ? AND is_active = 1;",
            (slug,),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "slug": row[1],
                    "original_url": row[2],
                    "created_at": row[3],
                    "expires_at": row[4],
                    "is_active": row[5],
                }
            return None

    async def create(self, conn: aiosqlite.Connection, slug: str, original_url: str, created_at: str) -> dict:
        """Insert a new URL and return its data."""
        await conn.execute(
            "INSERT INTO urls (slug, original_url, created_at) VALUES (?, ?, ?);",
            (slug, original_url, created_at),
        )
        await conn.commit()
        # Re-fetch the inserted row by slug
        async with conn.execute(
            "SELECT id, slug, original_url, created_at, expires_at, is_active FROM urls WHERE slug = ?;",
            (slug,),
        ) as cursor:
            row = await cursor.fetchone()
            return {
                "id": row[0],
                "slug": row[1],
                "original_url": row[2],
                "created_at": row[3],
                "expires_at": row[4],
                "is_active": row[5],
            }

    async def deactivate(self, conn: aiosqlite.Connection, slug: str) -> bool:
        """Soft-delete: set is_active = 0. Returns True if a row was actually updated."""
        cursor = await conn.execute(
            "UPDATE urls SET is_active = 0 WHERE slug = ? AND is_active = 1;",
            (slug,),
        )
        await conn.commit()
        return cursor.rowcount > 0

    async def slug_exists(self, conn: aiosqlite.Connection, slug: str) -> bool:
        """Check whether a slug already exists in the database."""
        async with conn.execute("SELECT 1 FROM urls WHERE slug = ?;", (slug,)) as cursor:
            row = await cursor.fetchone()
            return row is not None
