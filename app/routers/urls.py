"""
Router for URL creation.
"""

import secrets
import string

from fastapi import APIRouter, HTTPException, status

from app.database.connection import get_connection
from app.schemas import URLCreateRequest, URLCreateResponse

router = APIRouter(prefix="/api", tags=["urls"])


def _generate_short_code(length: int = 6) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


@router.post("/shorten", response_model=URLCreateResponse, status_code=status.HTTP_201_CREATED)
def create_short_url(payload: URLCreateRequest):
    original_url = str(payload.url)
    conn = get_connection()

    # Check if URL already exists
    existing = conn.execute(
        "SELECT short_code FROM urls WHERE original_url = ?", (original_url,)
    ).fetchone()

    if existing:
        short_code = existing["short_code"]
        conn.close()
        return URLCreateResponse(
            short_code=short_code,
            short_url=f"http://localhost:8000/{short_code}",
            original_url=original_url,
        )

    # Generate unique short code
    for _ in range(10):
        short_code = _generate_short_code()
        try:
            conn.execute(
                "INSERT INTO urls (short_code, original_url) VALUES (?, ?)",
                (short_code, original_url),
            )
            conn.commit()
            break
        except sqlite3.IntegrityError:
            continue
    else:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate unique short code",
        )

    conn.close()
    return URLCreateResponse(
        short_code=short_code,
        short_url=f"http://localhost:8000/{short_code}",
        original_url=original_url,
    )
