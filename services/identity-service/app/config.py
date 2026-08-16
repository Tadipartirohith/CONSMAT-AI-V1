"""Service configuration, loaded from environment."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "identity-service"
    api_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://consmat:consmat@localhost:5432/identity"
    # MUST match the JWT_SECRET of every other service so tokens validate everywhere.
    jwt_secret: str = "change-me-in-prod"
    jwt_alg: str = "HS256"
    access_token_ttl_min: int = 1440
    demo_password: str = "consmat123"


settings = Settings()
