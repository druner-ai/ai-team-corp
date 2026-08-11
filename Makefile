.PHONY: run test lint

run:
	uvicorn app.main:app --reload

test:
	pytest -v

lint:
	ruff check .
