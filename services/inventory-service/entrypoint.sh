#!/usr/bin/env sh
set -e

# Wait for Postgres, run migrations, seed reference data, then serve.
echo "[entrypoint] running migrations..."
alembic upgrade head

echo "[entrypoint] seeding materials..."
python -m app.seed

echo "[entrypoint] starting inventory-service..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
