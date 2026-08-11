from fastapi import APIRouter, Depends, HTTPException, status
from app.database import get_db
from app.schemas import URLStats

router = APIRouter()

@router.get("/stats/{short_code}", response_model=URLStats)
async def get_stats(short_code: str, db = Depends(get_db)):
    cursor = await db.execute("SELECT url, short_code, created_at, expires_at, clicks FROM urls WHERE short_code = ?", (short_code,))
    row = await cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Short code not found")
    return URLStats(
        url=row["url"],
        short_code=row["short_code"],
        created_at=row["created_at"],
        expires_at=row["expires_at"],
        clicks=row["clicks"]
    )
