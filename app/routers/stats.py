from fastapi import APIRouter, Depends, HTTPException
from sqlite3 import Connection
from app.database.connection import get_db
from app.schemas import URLStats
from app.crud import get_stats

router = APIRouter()


@router.get("/stats/{short_code}", response_model=URLStats)
async def url_stats(short_code: str, db: Connection = Depends(get_db)):
    stats = get_stats(db, short_code)
    if stats is None:
        raise HTTPException(status_code=404, detail="URL not found")
    return stats
