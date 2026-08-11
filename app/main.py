import random
import string
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.responses import RedirectResponse

from app.database import get_db, init_db, DATABASE_URL
from app.schemas import URLCreate, URLInfo, URLStats


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(lifespan=lifespan)


def generate_short_code(length: int = 6) -> str:
    """Generate a random alphanumeric short code."""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))


@app.post("/links", response_model=URLInfo, status_code=status.HTTP_201_CREATED)
async def create_short_link(payload: URLCreate, db=Depends(get_db)):
    # Generate a unique short code
    for _ in range(10):  # retry up to 10 times in case of collision
        short_code = generate_short_code()
        try:
            await db.execute(
                "INSERT INTO links (short_code, original_url) VALUES (?, ?)",
                (short_code, payload.url),
            )
            await db.commit()
            break
        except Exception:
            continue
    else:
        raise HTTPException(status_code=500, detail="Could not generate unique short code")

    short_url = f"http://localhost:8000/{short_code}"  # In production, use actual domain
    return URLInfo(short_code=short_code, short_url=short_url)


@app.get("/{short_code}")
async def redirect_to_original(short_code: str, db=Depends(get_db)):
    cursor = await db.execute(
        "SELECT original_url FROM links WHERE short_code = ?", (short_code,)
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Short link not found")

    original_url = row[0]
    # Increment access count
    await db.execute(
        "UPDATE links SET access_count = access_count + 1 WHERE short_code = ?",
        (short_code,),
    )
    await db.commit()

    return RedirectResponse(url=original_url, status_code=307)


@app.get("/stats/{short_code}", response_model=URLStats)
async def get_link_stats(short_code: str, db=Depends(get_db)):
    cursor = await db.execute(
        "SELECT original_url, created_at, access_count FROM links WHERE short_code = ?",
        (short_code,),
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Short link not found")

    return URLStats(
        original_url=row[0],
        created_at=row[1],
        access_count=row[2],
    )
