CREATE TABLE IF NOT EXISTS urls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    original_url TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_urls_original_url ON urls(original_url);

CREATE TABLE IF NOT EXISTS clicks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url_id INTEGER NOT NULL,
    clicked_at TEXT NOT NULL,
    referer TEXT,
    user_agent TEXT,
    ip TEXT,
    FOREIGN KEY (url_id) REFERENCES urls(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_clicks_url_id ON clicks(url_id);
CREATE INDEX IF NOT EXISTS idx_clicks_clicked_at ON clicks(clicked_at);
