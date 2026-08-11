.PHONY: run test lint

run:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

test:
	pytest -v

lint:
	ruff check app/ tests/ && ruff format app/ tests/
