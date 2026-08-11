from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from app.database import get_db
from datetime import datetime

router = APIRouter()

@router.get("/{short_code}")
async def redirect(short_code: str, db = Depends(get_db)):
    cursor = await db.execute("SELECT url, expires_at, clicks FROM urls WHERE short_code = ?", (short_code,))
    row = await cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Short code not found")
    url, expires_at, clicks = row
    if expires_at and datetime.utcnow() > datetime.fromisoformat(expires_at):
        raise HTTPException(status_code=410, detail="Link expired")
    await db.execute("UPDATE urls SET clicks = clicks + 1 WHERE short_code = ?", (short_code,))
    await db.commit()
    return RedirectResponse(url=url, status_code=302)
