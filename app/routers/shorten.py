import secrets
import string
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import URL
from app.schemas import URLCreate, URLResponse

router = APIRouter()

def generate_short_code(length: int = 6) -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

@router.post("/shorten", status_code=201, response_model=URLResponse)
async def shorten_url(url_data: URLCreate, db: AsyncSession = Depends(get_db)):
    # Generate a unique short code
    while True:
        code = generate_short_code()
        result = await db.execute(select(URL).where(URL.short_code == code))
        if not result.scalar_one_or_none():
            break

    db_url = URL(original_url=str(url_data.url), short_code=code)
    db.add(db_url)
    await db.commit()
    await db.refresh(db_url)

    return URLResponse(short_url=f"http://localhost:8000/{code}", short_code=code)
