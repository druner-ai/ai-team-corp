.PHONY: run test install migrate clean

install:
	pip install -r requirements.txt

run:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

test:
	pytest

migrate:
	mkdir -p data
	sqlite3 data/urls.db < migrations/001_init.sql

clean:
	rm -f data/urls.db
	find . -type d -name __pycache__ -exec rm -rf {} +
