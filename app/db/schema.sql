CREATE TABLE IF NOT EXISTS urls (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    code            TEXT NOT NULL UNIQUE,
    original_url    TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    clicks          INTEGER NOT NULL DEFAULT 0,
    last_clicked_at TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_urls_code ON urls(code);
CREATE INDEX IF NOT EXISTS idx_urls_created_at ON urls(created_at);
