from fastapi import APIRouter, Depends
from app.database import get_db

router = APIRouter()


@router.get("/health")
def health_check(db=Depends(get_db)):
    try:
        db.execute("SELECT 1")
        return {"status": "ok", "database": "connected"}
    except Exception:
        return {"status": "error", "database": "disconnected"}
