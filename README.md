# URL Shortener

A simple URL shortener service built with FastAPI and SQLite.

## Quick Start

1. Clone the repository.
2. Create a virtual environment and activate it.
3. Install dependencies: `pip install -e .`
4. Copy `.env.example` to `.env` and adjust if needed.
5. Run the server: `make run` or `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
6. Open http://localhost:8000/docs for interactive API documentation.

## Commands

- `make run` – start the development server
- `make test` – run tests
- `make lint` – run linter and formatter

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| DATABASE_PATH | ./urls.db | Path to SQLite database file |
| BASE_URL | http://localhost:8000 | Base URL for generated short links |
| SHORT_CODE_LENGTH | 6 | Length of generated short codes |
| MAX_URL_LENGTH | 2048 | Maximum allowed length of original URL |
