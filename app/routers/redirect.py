from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from app.database import get_db
import aiosqlite

router = APIRouter()


@router.get("/{short_code}")
async def redirect_to_url(short_code: str, request: Request, db: aiosqlite.Connection = Depends(get_db)):
    cursor = await db.execute("SELECT original_url FROM urls WHERE short_code = ?", (short_code,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Short URL not found")
    original_url = row[0]
    # Log click
    referer = request.headers.get("referer")
    user_agent = request.headers.get("user-agent")
    await db.execute(
        "INSERT INTO clicks (short_code, referer, user_agent) VALUES (?, ?, ?)",
        (short_code, referer, user_agent)
    )
    await db.commit()
    return RedirectResponse(url=original_url, status_code=302)
