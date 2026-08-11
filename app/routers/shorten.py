from fastapi import APIRouter, Depends, status
from sqlite3 import Connection
from app.database.connection import get_db
from app.schemas import URLCreate, URLInfo
from app.crud import create_short_url

router = APIRouter()


@router.post("/shorten", response_model=URLInfo, status_code=status.HTTP_201_CREATED)
async def shorten_url(payload: URLCreate, db: Connection = Depends(get_db)):
    return create_short_url(db, str(payload.url))
