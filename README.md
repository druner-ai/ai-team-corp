# URL Shortener Service

A simple, high-performance URL shortener built with FastAPI and SQLite.

## Features

- Create short URLs with optional custom codes and expiration
- Redirect to original URLs with 301 Moved Permanently
- Track click statistics (count, last click, recent clicks)
- Deactivate (soft delete) short URLs
- Health check endpoint
- In-memory caching for fast redirects

## Quick Start

### Prerequisites

- Python 3.11+
- pip

### Installation

bash
# Clone the repository
git clone <repo-url>
cd url-shortener

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt


### Configuration

Copy the example environment file and adjust as needed:

bash
cp .env.example .env


Available settings:

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_PATH` | `./data/shortener.db` | Path to SQLite database |
| `BASE_URL` | `http://localhost:8000` | Base URL for short links |
| `CACHE_TTL_SECONDS` | `300` | Cache TTL in seconds |
| `SHORT_CODE_LENGTH` | `6` | Length of generated short codes |
| `ALLOWED_ORIGINS` | (empty) | Comma-separated CORS origins |
| `LOG_LEVEL` | `INFO` | Logging level |

### Running

bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload


The API will be available at `http://localhost:8000`.

Interactive API docs: `http://localhost:8000/docs`

### Running Tests

bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/ -v


## API Endpoints

### Create Short URL

http
POST /api/urls
Content-Type: application/json

{
  "original_url": "https://example.com/very/long/path",
  "custom_code": "mylink",
  "expires_at": "2025-12-31T23:59:59Z"
}


### Redirect

http
GET /{short_code}


### Get URL Info

http
GET /api/urls/{short_code}


### Get Statistics

http
GET /api/urls/{short_code}/stats?limit=20


### Deactivate URL

http
DELETE /api/urls/{short_code}


### Health Check

http
GET /health


## Architecture

- **FastAPI** - Web framework with automatic OpenAPI docs
- **SQLite** - Embedded database with WAL mode for concurrency
- **aiosqlite** - Async SQLite driver
- **In-memory cache** - TTL-based caching for hot links
- **Base62 encoding** - Short code generation

## Project Structure


url-shortener/
├── app/
│   ├── api/          # Route handlers
│   ├── cache/        # In-memory cache
│   ├── repositories/ # Database access layer
│   ├── schemas/      # Pydantic models
│   ├── services/     # Business logic
│   └── utils/        # Utilities
├── tests/            # Test suite
├── requirements.txt
└── README.md


## License

MIT
