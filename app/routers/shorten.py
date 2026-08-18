from fastapi import APIRouter, Depends, HTTPException, status, Request
from app.schemas import URLCreate, URLResponse
from app.database import get_db
import secrets
import string
from datetime import datetime

router = APIRouter()

def generate_short_code(length=6):
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(length))

@router.post("/shorten", response_model=URLResponse, status_code=201)
async def create_short_url(data: URLCreate, request: Request, db = Depends(get_db)):
    url = str(data.url)
    short_code = data.custom_code or generate_short_code()
    cursor = await db.execute("SELECT short_code FROM urls WHERE short_code = ?", (short_code,))
    existing = await cursor.fetchone()
    if existing:
        if data.custom_code:
            raise HTTPException(status_code=409, detail="Custom code already exists")
        else:
            raise HTTPException(status_code=409, detail="Short code already exists")
    created_at = datetime.utcnow()
    expires_at = data.expires_at
    await db.execute(
        "INSERT INTO urls (short_code, url, created_at, expires_at, clicks) VALUES (?, ?, ?, ?, 0)",
        (short_code, url, created_at, expires_at)
    )
    await db.commit()
    short_url = f"{request.base_url}{short_code}"
    return URLResponse(short_code=short_code, url=url, short_url=short_url, created_at=created_at, expires_at=expires_at, clicks=0)

@router.delete("/{short_code}", status_code=204)
async def delete_short_url(short_code: str, db = Depends(get_db)):
    cursor = await db.execute("DELETE FROM urls WHERE short_code = ?", (short_code,))
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Short code not found")
    await db.commit()
    return
