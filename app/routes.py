"""
API routes for URL shortening, redirection, and statistics.
"""
import secrets
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from app.database import get_db
from app.schemas import URLCreate, URLResponse, ClickStats

router = APIRouter()


@router.post("/shorten", response_model=URLResponse, status_code=201)
async def create_short_url(payload: URLCreate, request: Request):
    db = await get_db()
    slug = payload.custom_slug or secrets.token_urlsafe(6)
    # Check if slug already exists
    cursor = await db.execute("SELECT slug FROM urls WHERE slug = ?", (slug,))
    existing = await cursor.fetchone()
    if existing:
        raise HTTPException(status_code=409, detail="Slug already exists")
    await db.execute(
        "INSERT INTO urls (slug, original_url) VALUES (?, ?)",
        (slug, str(payload.url)),
    )
    await db.commit()
    short_url = f"{request.base_url}{slug}"
    return URLResponse(
        slug=slug,
        original_url=str(payload.url),
        short_url=short_url,
        created_at=...,  # will be set by DB, but we can fetch
    )


@router.get("/{slug}")
async def redirect_to_url(slug: str, request: Request):
    db = await get_db()
    cursor = await db.execute("SELECT original_url FROM urls WHERE slug = ?", (slug,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="URL not found")
    # Log click
    client_ip = request.client.host if request.client else "unknown"
    await db.execute(
        "INSERT INTO clicks (slug, ip_address) VALUES (?, ?)", (slug, client_ip)
    )
    await db.commit()
    return RedirectResponse(url=row["original_url"], status_code=302)


@router.get("/stats/{slug}", response_model=ClickStats)
async def get_stats(slug: str):
    db = await get_db()
    cursor = await db.execute(
        "SELECT slug, original_url, created_at FROM urls WHERE slug = ?", (slug,)
    )
    url_row = await cursor.fetchone()
    if not url_row:
        raise HTTPException(status_code=404, detail="URL not found")
    cursor = await db.execute(
        "SELECT COUNT(*) as total FROM clicks WHERE slug = ?", (slug,)
    )
    total_clicks = (await cursor.fetchone())["total"]
    # Optionally fetch click details
    cursor = await db.execute(
        "SELECT clicked_at, ip_address FROM clicks WHERE slug = ? ORDER BY clicked_at DESC",
        (slug,),
    )
    clicks = [
        {"clicked_at": row["clicked_at"], "ip_address": row["ip_address"]}
        for row in await cursor.fetchall()
    ]
    return ClickStats(
        slug=url_row["slug"],
        original_url=url_row["original_url"],
        created_at=url_row["created_at"],
        total_clicks=total_clicks,
        clicks=clicks,
    )
