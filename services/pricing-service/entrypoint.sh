#!/usr/bin/env sh
set -e

echo "[entrypoint] ensuring database exists..."
python -m app.ensure_db

echo "[entrypoint] running migrations..."
alembic upgrade head

echo "[entrypoint] seeding margin rules..."
python -m app.seed

echo "[entrypoint] starting pricing-service..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
