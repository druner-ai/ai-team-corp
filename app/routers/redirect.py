from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlite3 import Connection
from app.database.connection import get_db
from app.crud import get_url_by_code, increment_clicks

router = APIRouter()


@router.get("/{short_code}")
async def redirect_to_url(short_code: str, db: Connection = Depends(get_db)):
    url_data = get_url_by_code(db, short_code)
    if url_data is None:
        raise HTTPException(status_code=404, detail="URL not found")
    increment_clicks(db, short_code)
    return RedirectResponse(url=url_data["original_url"], status_code=302)
