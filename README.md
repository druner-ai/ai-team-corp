# URL Shortener Service

A simple URL shortener service built with FastAPI and SQLite.

## Features

- Create short URLs from long URLs
- Redirect to original URLs using short codes
- View click statistics for each short URL
- Health check endpoint

## Requirements

- Python 3.11+

## Installation

```bash
pip install -e .
```

For development:
```bash
pip install -e ".[dev]"
```

## Configuration

Copy `.env.example` to `.env` and adjust the values:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_PATH` | `./urls.db` | Path to SQLite database file |
| `BASE_URL` | `http://localhost:8000` | Base URL for generating short URLs |
| `CODE_LENGTH` | `6` | Length of generated short codes |
| `MAX_RETRIES` | `3` | Maximum retries for code generation on collision |

## Running

```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

API documentation is available at:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Create Short URL
```
POST /api/v1/shorten
Content-Type: application/json

{
  "url": "https://example.com/very/long/path?query=1"
}
```

### Redirect
```
GET /{short_code}
```

### Statistics
```
GET /api/v1/stats/{short_code}
```

### Health Check
```
GET /api/v1/health
```

## Testing

```bash
pytest
```

## Project Structure

```
url-shortener/
├── src/
│   ├── main.py
│   ├── config.py
│   ├── api/
│   │   ├── router.py
│   │   └── v1/
│   │       ├── shorten.py
│   │       ├── redirect.py
│   │       ├── stats.py
│   │       └── health.py
│   ├── schemas/
│   │   ├── url.py
│   │   └── common.py
│   ├── services/
│   │   ├── url_service.py
│   │   └── code_generator.py
│   ├── repositories/
│   │   ├── url_repository.py
│   │   └── database.py
│   └── utils/
│       └── url_validator.py
├── tests/
│   ├── conftest.py
│   ├── test_shorten.py
│   ├── test_redirect.py
│   ├── test_stats.py
│   └── test_health.py
└── scripts/
    └── init_db.py
```
