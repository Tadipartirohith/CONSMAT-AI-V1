"""Service configuration: infra settings from env, payment-gateway config from config.yaml."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "payment-service"
    api_prefix: str = "/api/v1"
    database_url: str = "postgresql+psycopg://consmat:consmat@localhost:5432/payment"
    jwt_secret: str = "change-me-in-prod"
    jwt_alg: str = "HS256"
    # Path to the gateway config file (provider APIs + key env-var names).
    config_path: str = "config.yaml"


settings = Settings()


@lru_cache
def payment_config() -> dict:
    """Load the payments block from config.yaml."""
    path = Path(settings.config_path)
    if not path.is_absolute():
        path = Path(__file__).resolve().parent.parent / settings.config_path
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("payments", {})


def active_provider() -> tuple[str, dict]:
    """Return (provider_name, provider_settings) for the configured active provider."""
    cfg = payment_config()
    name = (cfg.get("provider") or "mock").lower()
    provider_cfg = (cfg.get("providers") or {}).get(name, {})
    return name, provider_cfg


def resolve_secret(env_name: str) -> str:
    """Resolve a provider secret from the environment by the name declared in config.yaml."""
    return os.environ.get(env_name, "")
