"""payment-service, config-driven payment gateway (Consmat AI V1)."""
from __future__ import annotations

from fastapi import FastAPI

from .config import settings
from .routers import payments

app = FastAPI(title="Consmat AI V1, Payment Service", version="0.1.0")
app.include_router(payments.router, prefix=settings.api_prefix)


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.service_name}


@app.get("/")
def root():
    return {"service": settings.service_name, "docs": "/docs", "api_prefix": settings.api_prefix}
