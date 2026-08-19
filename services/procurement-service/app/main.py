"""procurement-service, vendor registry + price lists (Consmat AI V1)."""
from __future__ import annotations

import threading
import time

from fastapi import FastAPI

from . import catalog_client, service
from .config import settings
from .db import SessionLocal
from .routers import procurement, vendors

app = FastAPI(title="Consmat AI V1, Procurement Service", version="0.1.0")
app.include_router(vendors.router, prefix=settings.api_prefix)
app.include_router(procurement.router, prefix=settings.api_prefix)


def _market_refresh_loop() -> None:
    """Refresh open-market offers across all categories on the configured interval (default 4h)."""
    while True:
        time.sleep(max(60, settings.scout_refresh_seconds))
        try:
            db = SessionLocal()
            try:
                mats = sorted({p["material_id"] for p in catalog_client.list_products()})
                if mats:
                    r = service.scan_markets(db, mats)
                    print(f"[market-refresh] {r}", flush=True)
            finally:
                db.close()
        except Exception as e:  # noqa: BLE001, a bad refresh must not kill the loop
            print(f"[market-refresh] error: {type(e).__name__}: {e}", flush=True)


@app.on_event("startup")
def _start_market_refresh() -> None:
    if settings.scout_refresh_enabled:
        threading.Thread(target=_market_refresh_loop, daemon=True).start()
        print("[market-refresh] open-market auto-scan started", flush=True)


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.service_name}


@app.get("/")
def root():
    return {"service": settings.service_name, "docs": "/docs", "api_prefix": settings.api_prefix}
