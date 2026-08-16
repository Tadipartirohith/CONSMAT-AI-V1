"""Service configuration, loaded from environment."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "procurement-service"
    api_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://consmat:consmat@localhost:5432/procurement"
    jwt_secret: str = "change-me-in-prod"
    jwt_alg: str = "HS256"
    # Optional: base URL of inventory-service, for catalog lookups (soft dependency).
    inventory_url: str = "http://localhost:8001"


settings = Settings()
