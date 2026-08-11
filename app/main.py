from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
import secrets
import string

from app.database import get_db, init_db
from app.schemas import ShortenRequest, ShortenResponse, StatsResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(lifespan=lifespan)


def generate_short_code(length: int = 6) -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


@app.post("/shorten", response_model=ShortenResponse)
async def shorten_url(body: ShortenRequest, db=Depends(get_db)):
    short_code = generate_short_code()
    try:
        await db.execute(
            "INSERT INTO urls (short_code, original_url) VALUES (?, ?)",
            (short_code, str(body.url)),
        )
        await db.commit()
    except Exception:
        # Если код уже существует (маловероятно), генерируем новый
        short_code = generate_short_code()
        await db.execute(
            "INSERT INTO urls (short_code, original_url) VALUES (?, ?)",
            (short_code, str(body.url)),
        )
        await db.commit()

    return ShortenResponse(
        short_code=short_code,
        short_url=f"http://localhost:8000/{short_code}",
        original_url=str(body.url),
    )


@app.get("/{short_code}")
async def redirect_to_url(short_code: str, request: Request, db=Depends(get_db)):
    cursor = await db.execute(
        "SELECT original_url FROM urls WHERE short_code = ?", (short_code,)
    )
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Short URL not found")

    original_url = row[0]

    # Логируем клик
    referer = request.headers.get("referer", "")
    user_agent = request.headers.get("user-agent", "")
    await db.execute(
        "INSERT INTO clicks (short_code, referer, user_agent) VALUES (?, ?, ?)",
        (short_code, referer, user_agent),
    )
    await db.commit()

    return RedirectResponse(url=original_url, status_code=302)


@app.get("/stats/{short_code}", response_model=StatsResponse)
async def get_stats(short_code: str, db=Depends(get_db)):
    cursor = await db.execute(
        "SELECT short_code, original_url, created_at FROM urls WHERE short_code = ?",
        (short_code,),
    )
    url_row = await cursor.fetchone()
    if not url_row:
        raise HTTPException(status_code=404, detail="Short URL not found")

    # Количество переходов
    cursor = await db.execute(
        "SELECT COUNT(*) FROM clicks WHERE short_code = ?", (short_code,)
    )
    click_count = (await cursor.fetchone())[0]

    # Последний переход
    cursor = await db.execute(
        "SELECT clicked_at FROM clicks WHERE short_code = ? ORDER BY clicked_at DESC LIMIT 1",
        (short_code,),
    )
    last_click_row = await cursor.fetchone()
    last_click = last_click_row[0] if last_click_row else None

    # Топ рефереров
    cursor = await db.execute(
        "SELECT referer, COUNT(*) as cnt FROM clicks WHERE short_code = ? GROUP BY referer ORDER BY cnt DESC LIMIT 5",
        (short_code,),
    )
    top_referers = [{"referer": row[0], "count": row[1]} async for row in cursor]

    # Топ User-Agent
    cursor = await db.execute(
        "SELECT user_agent, COUNT(*) as cnt FROM clicks WHERE short_code = ? GROUP BY user_agent ORDER BY cnt DESC LIMIT 5",
        (short_code,),
    )
    top_user_agents = [{"user_agent": row[0], "count": row[1]} async for row in cursor]

    return StatsResponse(
        short_code=url_row[0],
        original_url=url_row[1],
        created_at=url_row[2],
        click_count=click_count,
        last_click=last_click,
        top_referers=top_referers,
        top_user_agents=top_user_agents,
    )
