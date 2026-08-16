"""Client for pricing-service: fetch hub selling prices to compute real profitability."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

from .auth import service_token
from .config import settings


def selling_prices(tier: str | None) -> dict[str, float] | None:
    """Return {material_id: unit selling price} for a tier, or None if pricing-service is unavailable."""
    base = settings.pricing_url.rstrip("/")
    if not base:
        return None
    q = f"?tier={urllib.parse.quote(tier)}" if tier else ""
    url = f"{base}{settings.api_prefix}/selling-prices{q}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {service_token()}"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001, pricing is optional for analysis
        print(f"[pricing-client] unavailable: {e}", flush=True)
        return None
