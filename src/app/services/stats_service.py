from typing import Optional

import aiosqlite

from ..repositories import clicks_repo, urls_repo


async def get_stats(conn: aiosqlite.Connection, code: str) -> Optional[dict]:
    """Retrieve statistics for a given short code."""
    url = await urls_repo.get_by_code(conn, code)
    if url is None:
        return None

    url_id = url["id"]
    total = await clicks_repo.count_clicks(conn, url_id)
    last = await clicks_repo.last_click_at(conn, url_id)
    referers = await clicks_repo.top_referers(conn, url_id)
    uas = await clicks_repo.top_user_agents(conn, url_id)

    return {
        "code": url["code"],
        "original_url": url["original_url"],
        "created_at": url["created_at"],
        "total_clicks": total,
        "last_click_at": last,
        "top_referers": referers,
        "top_user_agents": uas,
    }
