.PHONY: run test lint docker-build

run:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/ -v

lint:
	ruff check app/ tests/

docker-build:
	docker build -t health-check-service:1.0.0 .
