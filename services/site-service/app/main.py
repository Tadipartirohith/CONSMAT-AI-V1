"""site-service, spokes, consumers, sites, plans, phases, JIT dispatch (Consmat AI V1)."""
from __future__ import annotations

import threading
import time

from fastapi import FastAPI

from . import service
from .config import settings
from .db import SessionLocal
from .routers import sites

app = FastAPI(title="Consmat AI V1, Site Service", version="0.1.0")
app.include_router(sites.router, prefix=settings.api_prefix)


def _scheduler_loop() -> None:
    """Background JIT scheduler: periodically warn + pre-dispatch next-phase materials by phase dates."""
    while True:
        time.sleep(max(5, settings.scheduler_interval_seconds))
        try:
            db = SessionLocal()
            try:
                result = service.run_scheduler_tick(db)
                if result["actions"]:
                    print(f"[scheduler] {result['actions']}", flush=True)
            finally:
                db.close()
        except Exception as e:  # noqa: BLE001, a bad tick must not kill the loop
            print(f"[scheduler] tick error: {type(e).__name__}: {e}", flush=True)


@app.on_event("startup")
def _start_scheduler() -> None:
    if settings.scheduler_enabled:
        threading.Thread(target=_scheduler_loop, daemon=True).start()
        print("[scheduler] JIT dispatch scheduler started", flush=True)


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.service_name}


@app.get("/")
def root():
    return {"service": settings.service_name, "docs": "/docs", "api_prefix": settings.api_prefix}
