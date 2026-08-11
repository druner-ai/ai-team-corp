"""Database connection and initialization.

Uses sqlite3 (synchronous) with FastAPI dependency injection.
Tests override get_db via dependency_overrides.
"""

import sqlite3
from pathlib import Path

# Database file path
BASE_DIR = Path(__file__).parent.parent
DATABASE_PATH = BASE_DIR / "data.db"


def get_db():
    """Dependency for FastAPI — creates a new connection per request.
    
    Yields a sqlite3.Connection with row_factory set to sqlite3.Row
    for dict-like access to columns.
    """
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Initialize database schema.
    
    Creates tables and indexes if they don't exist.
    Called during application startup.
    """
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.execute("PRAGMA foreign_keys = ON")
    
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            short_code TEXT UNIQUE NOT NULL,
            original_url TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS clicks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url_id INTEGER,
            clicked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT,
            user_agent TEXT,
            FOREIGN KEY (url_id) REFERENCES urls(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_urls_short_code ON urls(short_code);
        CREATE INDEX IF NOT EXISTS idx_clicks_url_id ON clicks(url_id);
    """)
    conn.commit()
    conn.close()
