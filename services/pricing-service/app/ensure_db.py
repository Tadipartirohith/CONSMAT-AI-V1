"""Create this service's database if it doesn't exist yet (database-per-service, D10)."""
from __future__ import annotations

from urllib.parse import urlparse

import psycopg

from .config import settings


def ensure_database() -> None:
    url = settings.database_url.replace("postgresql+psycopg://", "postgresql://")
    parsed = urlparse(url)
    dbname = parsed.path.lstrip("/")
    admin_url = url.rsplit("/", 1)[0] + "/postgres"
    with psycopg.connect(admin_url, autocommit=True) as conn:
        exists = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,)).fetchone()
        if exists:
            print(f"[ensure_db] database '{dbname}' already exists")
            return
        conn.execute(f'CREATE DATABASE "{dbname}"')
        print(f"[ensure_db] created database '{dbname}'")


if __name__ == "__main__":
    ensure_database()
