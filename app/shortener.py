import secrets
import string
from app.database import get_connection


def generate_short_code(length: int = 6) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


async def create_short_url(original_url: str) -> tuple[str, str]:
    conn = await get_connection()
    while True:
        code = generate_short_code()
        try:
            await conn.execute(
                "INSERT INTO urls (short_code, original_url) VALUES (?, ?)",
                (code, original_url),
            )
            await conn.commit()
            return code, original_url
        except Exception:
            # code collision, retry
            continue


async def get_original_url(short_code: str) -> str | None:
    conn = await get_connection()
    cursor = await conn.execute(
        "SELECT original_url FROM urls WHERE short_code = ?", (short_code,)
    )
    row = await cursor.fetchone()
    return row["original_url"] if row else None


async def increment_clicks(short_code: str) -> None:
    conn = await get_connection()
    await conn.execute(
        "UPDATE urls SET clicks = clicks + 1 WHERE short_code = ?", (short_code,)
    )
    await conn.commit()


async def get_stats(short_code: str) -> dict | None:
    conn = await get_connection()
    cursor = await conn.execute(
        "SELECT short_code, original_url, created_at, clicks FROM urls WHERE short_code = ?",
        (short_code,),
    )
    row = await cursor.fetchone()
    if row:
        return {
            "short_code": row["short_code"],
            "original_url": row["original_url"],
            "created_at": row["created_at"],
            "clicks": row["clicks"],
        }
    return None
