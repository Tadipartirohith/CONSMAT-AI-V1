"""procurement-service, vendor registry + price lists (Consmat AI V1)."""
from __future__ import annotations

from fastapi import FastAPI

from .config import settings
from .routers import procurement, vendors

app = FastAPI(title="Consmat AI V1, Procurement Service", version="0.1.0")
app.include_router(vendors.router, prefix=settings.api_prefix)
app.include_router(procurement.router, prefix=settings.api_prefix)


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.service_name}


@app.get("/")
def root():
    return {"service": settings.service_name, "docs": "/docs", "api_prefix": settings.api_prefix}
