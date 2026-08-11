from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl
from app.database import init_db, close_db, get_connection
import secrets
import string

app = FastAPI()


class URLRequest(BaseModel):
    url: HttpUrl


class URLResponse(BaseModel):
    short_code: str
    short_url: str
    original_url: str


class StatsResponse(BaseModel):
    original_url: str
    created_at: str
    clicks: int


def generate_short_code(length: int = 6) -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


@app.on_event("startup")
async def startup():
    await init_db()


@app.on_event("shutdown")
async def shutdown():
    await close_db()


@app.post("/shorten", response_model=URLResponse, status_code=201)
async def shorten_url(request: URLRequest):
    conn = await get_connection()
    short_code = generate_short_code()
    original_url = str(request.url)

    # Проверяем уникальность short_code
    while True:
        cursor = await conn.execute(
            "SELECT id FROM urls WHERE short_code = ?", (short_code,)
        )
        row = await cursor.fetchone()
        if row is None:
            break
        short_code = generate_short_code()

    await conn.execute(
        "INSERT INTO urls (short_code, original_url) VALUES (?, ?)",
        (short_code, original_url),
    )
    await conn.commit()

    short_url = f"http://localhost:8000/{short_code}"
    return URLResponse(
        short_code=short_code,
        short_url=short_url,
        original_url=original_url,
    )


@app.get("/{short_code}")
async def redirect_to_url(short_code: str, request: Request):
    conn = await get_connection()
    cursor = await conn.execute(
        "SELECT original_url FROM urls WHERE short_code = ?", (short_code,)
    )
    row = await cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Short code not found")

    original_url = row[0]

    # Увеличиваем счётчик кликов
    await conn.execute(
        "UPDATE urls SET clicks = clicks + 1 WHERE short_code = ?", (short_code,)
    )
    await conn.commit()

    return RedirectResponse(url=original_url, status_code=302)


@app.get("/stats/{short_code}", response_model=StatsResponse)
async def get_stats(short_code: str):
    conn = await get_connection()
    cursor = await conn.execute(
        "SELECT original_url, created_at, clicks FROM urls WHERE short_code = ?",
        (short_code,),
    )
    row = await cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Short code not found")

    return StatsResponse(
        original_url=row[0],
        created_at=row[1],
        clicks=row[2],
    )
