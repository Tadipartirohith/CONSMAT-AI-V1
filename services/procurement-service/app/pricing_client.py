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


def product_selling_prices(product_ids: list[str], tier: str | None = None) -> dict[str, float]:
    """Return {product_id: unit SELLING price} (no cost/margin) for BOM alternatives. Empty on failure."""
    base = settings.pricing_url.rstrip("/")
    ids = [p for p in (product_ids or []) if p]
    if not base or not ids:
        return {}
    url = f"{base}{settings.api_prefix}/selling-prices-products"
    data = json.dumps({"product_ids": ids, "tier": tier}).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {service_token()}"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001, pricing is optional
        print(f"[pricing-client] product prices unavailable: {e}", flush=True)
        return {}
