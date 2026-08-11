import sqlite3
from pathlib import Path

DATABASE_PATH = Path("urls.db")


def get_db():
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    schema_path = Path(__file__).parent.parent / "sql" / "init.sql"
    if schema_path.exists():
        with open(schema_path) as f:
            conn.executescript(f.read())
    conn.commit()
    conn.close()
