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
    # inventory-service base URL (procurement receipts post inbound here).
    inventory_url: str = "http://localhost:8001"
    # pricing-service base URL (fetch hub selling prices for profitability).
    pricing_url: str = "http://localhost:8004"

    # --- Hub LLM (procurement intelligence). stub = deterministic only, no key. ---
    ai_provider: str = "stub"          # stub | gemini | openai | groq | openrouter | anthropic | openai-compat
    ai_api_key: str = ""
    ai_model: str = ""
    ai_base_url: str = ""

    # Price-scout (external market intelligence): auto | stub | llm | serpapi (serpapi = extension point)
    scout_provider: str = "auto"


settings = Settings()
