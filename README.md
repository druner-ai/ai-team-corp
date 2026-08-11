# URL Shortener

A simple URL shortener built with FastAPI and SQLite.

## Setup

1. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   bash scripts/run.sh
   ```
   or directly:
   ```bash
   uvicorn src.app.main:app --host 0.0.0.0 --port 8000
   ```
4. Open [http://localhost:8000/docs](http://localhost:8000/docs) for interactive API documentation.

## Testing

Install dev dependencies:
```bash
pip install -r requirements-dev.txt
pytest
```

## Environment Variables
See `.env.example` for configuration options.
