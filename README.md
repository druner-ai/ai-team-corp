# URL Shortener

A simple URL shortener service built with FastAPI and SQLite.

## Quick Start with Docker

1. Clone the repository.
2. Copy `.env.example` to `.env` and adjust settings if needed.
3. Run `docker compose up --build`.
4. The service will be available at `http://localhost:8000`.

## Local Development

1. Install dependencies: `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and adjust settings if needed.
3. Run the server: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`

## Testing

Install dev dependencies: `pip install -r requirements-dev.txt`
Run tests: `pytest`
