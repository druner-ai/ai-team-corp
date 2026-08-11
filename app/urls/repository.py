import sqlite3
from typing import Optional
from datetime import datetime, timedelta


def create_url(db: sqlite3.Connection, short_code: str, original_url: str, expires_at: Optional[str] = None) -> int:
    now = datetime.utcnow().isoformat() + "Z"
    cursor = db.execute(
        "INSERT INTO urls (short_code, original_url, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (short_code, original_url, now, expires_at)
    )
    db.commit()
    return cursor.lastrowid


def get_url_by_code(db: sqlite3.Connection, short_code: str) -> Optional[dict]:
    row = db.execute(
        "SELECT * FROM urls WHERE short_code = ?",
        (short_code,)
    ).fetchone()
    return dict(row) if row else None


def deactivate_url(db: sqlite3.Connection, short_code: str) -> bool:
    cursor = db.execute(
        "UPDATE urls SET is_active = 0 WHERE short_code = ? AND is_active = 1",
        (short_code,)
    )
    db.commit()
    return cursor.rowcount > 0


def url_exists(db: sqlite3.Connection, short_code: str) -> bool:
    row = db.execute(
        "SELECT 1 FROM urls WHERE short_code = ?",
        (short_code,)
    ).fetchone()
    return row is not None


def record_click(db: sqlite3.Connection, url_id: int, ip_address: Optional[str] = None, user_agent: Optional[str] = None):
    now = datetime.utcnow().isoformat() + "Z"
    db.execute(
        "INSERT INTO clicks (url_id, clicked_at, ip_address, user_agent) VALUES (?, ?, ?, ?)",
        (url_id, now, ip_address, user_agent)
    )
    db.commit()


def get_click_stats(db: sqlite3.Connection, url_id: int) -> dict:
    total = db.execute(
        "SELECT COUNT(*) FROM clicks WHERE url_id = ?",
        (url_id,)
    ).fetchone()[0]

    last = db.execute(
        "SELECT clicked_at FROM clicks WHERE url_id = ? ORDER BY clicked_at DESC LIMIT 1",
        (url_id,)
    ).fetchone()
    last_click_at = last[0] if last else None

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + "Z"
    today = db.execute(
        "SELECT COUNT(*) FROM clicks WHERE url_id = ? AND clicked_at >= ?",
        (url_id, today_start)
    ).fetchone()[0]

    seven_days_ago = (datetime.utcnow() - timedelta(days=7)).isoformat() + "Z"
    last_7 = db.execute(
        "SELECT COUNT(*) FROM clicks WHERE url_id = ? AND clicked_at >= ?",
        (url_id, seven_days_ago)
    ).fetchone()[0]

    return {
        "total_clicks": total,
        "last_click_at": last_click_at,
        "clicks_today": today,
        "clicks_last_7_days": last_7
    }
