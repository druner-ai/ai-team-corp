# URL Shortener

A simple URL shortener service built with FastAPI and SQLite.

## Quick Start with Docker

1. Clone the repository.
2. Run `docker compose up`.
3. The service will be available at `http://localhost:8000`.

## Local Development

1. Create a virtual environment: `python -m venv venv`
2. Activate it: `source venv/bin/activate` (Linux/Mac) or `venv\Scripts\activate` (Windows)
3. Install dependencies: `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and adjust settings if needed.
5. Run the server: `uvicorn app.main:app --reload`

## API Endpoints

- `POST /links` - Create a short link
- `GET /{slug}` - Redirect to original URL
- `GET /stats/{slug}` - Get click statistics
- `GET /health` - Health check

## Testing

Install dev dependencies: `pip install -r requirements-dev.txt`
Run tests: `pytest`
