#!/bin/bash
set -e

# Run database migrations
echo "Running Alembic migrations..."
alembic upgrade head

# Start Uvicorn server
exec "$@"