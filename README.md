# URL Shortener

A simple URL shortener service built with FastAPI and SQLite.

## Setup

1. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and adjust settings if needed.
3. Run the server:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
4. Open http://localhost:8000/docs for interactive API documentation.

## Testing

```bash
pip install -r requirements-dev.txt
pytest
```
