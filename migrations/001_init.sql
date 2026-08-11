CREATE TABLE IF NOT EXISTS urls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,
    original_url TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at TEXT,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_urls_slug ON urls(slug);
CREATE INDEX IF NOT EXISTS idx_urls_created_at ON urls(created_at);

CREATE TABLE IF NOT EXISTS clicks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url_id INTEGER NOT NULL,
    clicked_at TEXT NOT NULL DEFAULT (datetime('now')),
    ip_address TEXT,
    user_agent TEXT,
    referer TEXT,
    FOREIGN KEY (url_id) REFERENCES urls(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_clicks_url_id ON clicks(url_id);
CREATE INDEX IF NOT EXISTS idx_clicks_clicked_at ON clicks(clicked_at);
