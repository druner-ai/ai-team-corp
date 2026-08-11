from fastapi import APIRouter, Depends, HTTPException
import aiosqlite

from ..database import get_db
from ..models import ShortenRequest, ShortenResponse
from ..services.url_service import create_short_url

router = APIRouter()


@router.post("/shorten", response_model=ShortenResponse, status_code=201)
async def shorten_url(
    request: ShortenRequest,
    conn: aiosqlite.Connection = Depends(get_db),
):
    try:
        result = await create_short_url(
            conn=conn,
            url=request.url,
            custom_code=request.custom_code,
            expires_at=request.expires_at,
        )
        return result
    except ValueError as e:
        if "already in use" in str(e):
            raise HTTPException(status_code=409, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
