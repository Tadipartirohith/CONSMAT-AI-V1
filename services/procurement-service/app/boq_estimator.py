"""External BOQ estimator: a *second* Bill of Quantities from another app, used to cross-check the SE's BOQ.

Pluggable provider (carried in the same spirit as the payment/scout providers). The **stub** derives a
deterministic second BOQ from the SE BOQ (a stable per-line variance) so the >5% reconciliation flow is
fully demonstrable without a real integration. A real HTTP provider (`BOQ_PROVIDER=external` +
`BOQ_API_URL`/`BOQ_API_KEY`) is a clearly-marked extension point; this service never hardcodes keys.
"""
from __future__ import annotations

import json
import urllib.request

from .config import settings


def _variance(key: str) -> float:
    """Deterministic factor in ~[0.90, 1.12] from a stable hash of the product id."""
    h = sum(ord(c) for c in (key or "x"))
    return round(0.90 + ((h * 37) % 23) / 100.0, 3)


def estimate(lines: list[dict]) -> dict:
    """Return {"provider", "lines":[{product_id, material_id, product_name, phase_seq, total_qty}]}."""
    provider = (settings.boq_provider or "stub").lower()
    if provider == "external" and settings.boq_api_url:
        try:  # extension point: hand the design/BOQ context to the external app
            headers = {"Content-Type": "application/json"}
            if settings.boq_api_key:
                headers["Authorization"] = f"Bearer {settings.boq_api_key}"
            req = urllib.request.Request(settings.boq_api_url.rstrip("/") + "/estimate",
                                         data=json.dumps({"lines": lines}).encode("utf-8"),
                                         method="POST", headers=headers)
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return {"provider": "external", "lines": data.get("lines", [])}
        except Exception as e:  # noqa: BLE001, external is best-effort; fall back to the stub
            print(f"[boq-estimator] external provider failed, using stub: {type(e).__name__}: {e}", flush=True)
    out = []
    for ln in lines:
        f = _variance(ln.get("product_id") or ln.get("material_id", ""))
        out.append({"product_id": ln.get("product_id", ""), "material_id": ln.get("material_id", ""),
                    "product_name": ln.get("product_name", ""), "phase_seq": ln.get("phase_seq", 0),
                    "total_qty": round(float(ln.get("total_qty", 0)) * f, 3)})
    return {"provider": "stub", "lines": out}
