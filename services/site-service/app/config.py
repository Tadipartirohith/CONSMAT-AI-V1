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
    # identity-service base URL: onboarding creates a consumer login here.
    identity_url: str = "http://localhost:8005"
    # payment-service base URL: delivery confirmation releases the project's held escrow here.
    payment_url: str = "http://localhost:8006"
    # procurement-service base URL: the external second-BOQ estimator lives here.
    procurement_url: str = "http://localhost:8002"
    demo_password: str = "consmat123"  # temp password issued to a newly onboarded consumer
    # JIT dispatch scheduler: warn 3 days before a phase ends and pre-dispatch the next phase.
    scheduler_enabled: bool = True
    scheduler_interval_seconds: int = 60
    # Nudge the field team when a delivered shipment stays unconfirmed for this many days.
    confirm_reminder_days: int = 3


settings = Settings()
