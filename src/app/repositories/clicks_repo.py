from typing import Optional, List, Dict

import aiosqlite


async def insert_click(
    conn: aiosqlite.Connection,
    url_id: int,
    clicked_at: str,
    referer: Optional[str],
    user_agent: Optional[str],
    ip: Optional[str],
) -> None:
    """Record a click event."""
    await conn.execute(
        "INSERT INTO clicks (url_id, clicked_at, referer, user_agent, ip) VALUES (?, ?, ?, ?, ?)",
        (url_id, clicked_at, referer, user_agent, ip),
    )
    await conn.commit()


async def count_clicks(conn: aiosqlite.Connection, url_id: int) -> int:
    """Return total number of clicks for a given url_id."""
    cursor = await conn.execute(
        "SELECT COUNT(*) FROM clicks WHERE url_id = ?", (url_id,)
    )
    row = await cursor.fetchone()
    return row[0] if row else 0


async def last_click_at(conn: aiosqlite.Connection, url_id: int) -> Optional[str]:
    """Return ISO timestamp of the most recent click."""
    cursor = await conn.execute(
        "SELECT clicked_at FROM clicks WHERE url_id = ? ORDER BY clicked_at DESC LIMIT 1",
        (url_id,),
    )
    row = await cursor.fetchone()
    return row[0] if row else None


async def top_referers(
    conn: aiosqlite.Connection, url_id: int, limit: int = 10
) -> List[Dict[str, object]]:
    """Return top referer values and their counts."""
    cursor = await conn.execute(
        """
        SELECT COALESCE(referer, 'direct') AS ref, COUNT(*) AS cnt
        FROM clicks
        WHERE url_id = ?
        GROUP BY ref
        ORDER BY cnt DESC
        LIMIT ?
        """,
        (url_id, limit),
    )
    rows = await cursor.fetchall()
    return [{"referer": ref, "count": cnt} for ref, cnt in rows]


async def top_user_agents(
    conn: aiosqlite.Connection, url_id: int, limit: int = 10
) -> List[Dict[str, object]]:
    """Return top user-agent strings and their counts."""
    cursor = await conn.execute(
        """
        SELECT COALESCE(user_agent, 'Unknown') AS ua, COUNT(*) AS cnt
        FROM clicks
        WHERE url_id = ?
        GROUP BY ua
        ORDER BY cnt DESC
        LIMIT ?
        """,
        (url_id, limit),
    )
    rows = await cursor.fetchall()
    return [{"user_agent": ua, "count": cnt} for ua, cnt in rows]
