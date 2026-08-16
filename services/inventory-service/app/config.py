"""Service configuration, loaded from environment."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "inventory-service"
    api_prefix: str = "/api/v1"
    # e.g. postgresql+psycopg://consmat:consmat@localhost:5432/inventory
    database_url: str = "postgresql+psycopg://consmat:consmat@localhost:5432/inventory"
    jwt_secret: str = "change-me-in-prod"
    jwt_alg: str = "HS256"


settings = Settings()
