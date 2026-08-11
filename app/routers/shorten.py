import secrets
from fastapi import APIRouter, Depends, HTTPException
from app.database import get_db
from app.schemas import ShortenRequest, ShortenResponse
import aiosqlite

router = APIRouter()


def generate_short_code(length=6):
    return secrets.token_urlsafe(length)[:length]


@router.post("/shorten", response_model=ShortenResponse)
async def shorten_url(request: ShortenRequest, db: aiosqlite.Connection = Depends(get_db)):
    original_url = str(request.url)
    # Check if already exists
    cursor = await db.execute("SELECT short_code FROM urls WHERE original_url = ?", (original_url,))
    row = await cursor.fetchone()
    if row:
        short_code = row[0]
    else:
        # Generate unique short code
        for _ in range(10):  # retry
            short_code = generate_short_code()
            try:
                await db.execute("INSERT INTO urls (short_code, original_url) VALUES (?, ?)", (short_code, original_url))
                await db.commit()
                break
            except aiosqlite.IntegrityError:
                continue
        else:
            raise HTTPException(status_code=500, detail="Could not generate unique short code")
    short_url = f"http://localhost:8000/{short_code}"
    return ShortenResponse(short_code=short_code, short_url=short_url)
