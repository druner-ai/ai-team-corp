from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas import URLCreate, URLInfo, URLStats
from app import crud

router = APIRouter()


@router.post("/shorten", response_model=URLInfo, status_code=201)
async def shorten_url(payload: URLCreate, request: Request, db: AsyncSession = Depends(get_db)):
    db_url = await crud.create_short_url(db, str(payload.url))
    short_url = str(request.base_url) + db_url.short_code
    return URLInfo(
        short_code=db_url.short_code,
        original_url=db_url.original_url,
        short_url=short_url,
        created_at=db_url.created_at,
        last_visited_at=db_url.last_visited_at,
        visits=db_url.visits,
    )


@router.get("/{short_code}")
async def redirect_to_url(short_code: str, db: AsyncSession = Depends(get_db)):
    db_url = await crud.get_url_by_code(db, short_code)
    if not db_url:
        raise HTTPException(status_code=404, detail="URL not found")
    await crud.increment_visits(db, db_url)
    return {"url": db_url.original_url, "status_code": 301, "headers": {"Location": db_url.original_url}}


@router.get("/stats/{short_code}", response_model=URLStats)
async def get_url_stats(short_code: str, db: AsyncSession = Depends(get_db)):
    db_url = await crud.get_url_by_code(db, short_code)
    if not db_url:
        raise HTTPException(status_code=404, detail="URL not found")
    return URLStats(
        short_code=db_url.short_code,
        original_url=db_url.original_url,
        short_url=f"http://localhost/{db_url.short_code}",  # base URL not known here without request
        created_at=db_url.created_at,
        last_visited_at=db_url.last_visited_at,
        visits=db_url.visits,
    )
