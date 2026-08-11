CREATE TABLE IF NOT EXISTS urls (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    short_code      TEXT NOT NULL UNIQUE,
    original_url    TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    last_visited_at TEXT,
    clicks          INTEGER NOT NULL DEFAULT 0
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_urls_short_code ON urls(short_code);
CREATE INDEX IF NOT EXISTS idx_urls_created_at ON urls(created_at);
