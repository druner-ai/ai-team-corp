import aiosqlite
from typing import Optional
import logging

logger = logging.getLogger(__name__)


async def insert_click(conn: aiosqlite.Connection, link_id: int, ip_address: Optional[str], user_agent: Optional[str]):
    cursor = await conn.execute(
        "INSERT INTO clicks (link_id, ip_address, user_agent) VALUES (?, ?, ?)",
        (link_id, ip_address, user_agent)
    )
    await conn.commit()
    if cursor.lastrowid is None:
        logger.error("Failed to insert click: no lastrowid returned")
        raise RuntimeError("Failed to insert click")


async def get_stats_by_slug(conn: aiosqlite.Connection, slug: str) -> Optional[dict]:
    cursor = await conn.execute("""
        SELECT 
            l.slug,
            l.original_url,
            l.created_at,
            COUNT(c.id) as clicks_count,
            MAX(c.clicked_at) as last_click_at,
            (SELECT c2.ip_address FROM clicks c2 WHERE c2.link_id = l.id ORDER BY c2.clicked_at DESC LIMIT 1) as last_click_ip,
            (SELECT c2.user_agent FROM clicks c2 WHERE c2.link_id = l.id ORDER BY c2.clicked_at DESC LIMIT 1) as last_click_user_agent
        FROM links l
        LEFT JOIN clicks c ON c.link_id = l.id
        WHERE l.slug = ?
        GROUP BY l.id
    """, (slug,))
    row = await cursor.fetchone()
    if row:
        return dict(row)
    return None
