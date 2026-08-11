from fastapi import APIRouter, Depends, HTTPException
from app.database import get_db
from app.schemas import StatsResponse
import aiosqlite

router = APIRouter()


@router.get("/{short_code}/stats", response_model=StatsResponse)
async def get_stats(short_code: str, db: aiosqlite.Connection = Depends(get_db)):
    cursor = await db.execute("SELECT original_url, created_at FROM urls WHERE short_code = ?", (short_code,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Short URL not found")
    original_url, created_at = row
    # Count clicks
    cursor = await db.execute("SELECT COUNT(*) FROM clicks WHERE short_code = ?", (short_code,))
    clicks = (await cursor.fetchone())[0]
    # Last click
    cursor = await db.execute("SELECT MAX(clicked_at) FROM clicks WHERE short_code = ?", (short_code,))
    last_clicked_at = (await cursor.fetchone())[0]
    # Top referers
    cursor = await db.execute(
        "SELECT referer, COUNT(*) as cnt FROM clicks WHERE short_code = ? AND referer IS NOT NULL GROUP BY referer ORDER BY cnt DESC LIMIT 5",
        (short_code,)
    )
    top_referers = [(row[0], row[1]) async for row in cursor]
    # Top user agents
    cursor = await db.execute(
        "SELECT user_agent, COUNT(*) as cnt FROM clicks WHERE short_code = ? AND user_agent IS NOT NULL GROUP BY user_agent ORDER BY cnt DESC LIMIT 5",
        (short_code,)
    )
    top_user_agents = [(row[0], row[1]) async for row in cursor]
    return StatsResponse(
        short_code=short_code,
        original_url=original_url,
        created_at=created_at,
        clicks=clicks,
        last_clicked_at=last_clicked_at,
        top_referers=top_referers,
        top_user_agents=top_user_agents
    )
