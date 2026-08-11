import aiosqlite
from typing import Optional
import logging

logger = logging.getLogger(__name__)


async def insert_link(conn: aiosqlite.Connection, slug: str, original_url: str) -> int:
    cursor = await conn.execute(
        "INSERT INTO links (slug, original_url) VALUES (?, ?)",
        (slug, original_url)
    )
    await conn.commit()
    if cursor.lastrowid is None:
        logger.error("Failed to insert link: no lastrowid returned")
        raise RuntimeError("Failed to insert link")
    return cursor.lastrowid


async def get_link_by_slug(conn: aiosqlite.Connection, slug: str) -> Optional[dict]:
    cursor = await conn.execute(
        "SELECT id, slug, original_url, created_at FROM links WHERE slug = ?",
        (slug,)
    )
    row = await cursor.fetchone()
    if row:
        return dict(row)
    return None
