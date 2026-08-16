"""Service configuration, loaded from environment."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "pricing-service"
    api_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://consmat:consmat@localhost:5432/pricing"
    jwt_secret: str = "change-me-in-prod"
    jwt_alg: str = "HS256"
    # inventory-service base URL: landed cost (avg_cost) + catalog come from here.
    inventory_url: str = "http://localhost:8001"
    # fallback margin (%) when no rule matches at all.
    default_margin_pct: float = 10.0


settings = Settings()
