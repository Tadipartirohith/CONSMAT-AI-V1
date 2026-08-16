"""Service configuration, loaded from environment."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "site-service"
    api_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://consmat:consmat@localhost:5432/site"
    jwt_secret: str = "change-me-in-prod"
    jwt_alg: str = "HS256"
    # inventory-service base URL: catalog lookups + phase dispatch (outbound) go here.
    inventory_url: str = "http://localhost:8001"


settings = Settings()
