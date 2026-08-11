# URL Shortener

A simple URL shortener service built with FastAPI and SQLite.

## Features

- Shorten long URLs to 6-character codes
- Redirect with 307 Temporary Redirect
- View click statistics

## Quick Start

### Using Docker Compose (recommended)

1. Copy `.env.example` to `.env` and adjust if needed.
2. Run:
   ```bash
   docker compose up
   ```
3. The API is available at http://localhost:8000.
4. Interactive documentation: http://localhost:8000/docs

### Local development

1. Install dependencies: `pip install -e .`
2. Run the server: `uvicorn src.main:app --reload`
3. Open http://localhost:8000/docs

## Environment Variables

| Variable      | Default                     | Description                     |
|---------------|-----------------------------|---------------------------------|
| `BASE_URL`    | `http://localhost:8000`     | Base URL for generated short links |
| `DB_PATH`     | `./data/urls.db`            | Path to SQLite database file    |
| `CODE_LENGTH` | `6`                         | Length of generated short codes |
| `DB_POOL_SIZE`| `5`                         | Number of database connections  |

Copy `.env.example` to `.env` and adjust as needed.

## Testing

```bash
pip install -e ".[dev]"
pytest
```

## CI/CD

GitHub Actions workflow runs on push to `master` and `ai-team/**` branches, and on pull requests to `master`.
- **test**: runs pytest on Python 3.12
- **build**: builds the Docker image (only on push to the allowed branches)
