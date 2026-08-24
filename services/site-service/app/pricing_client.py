"""Client for pricing-service: price a finalized BOQ to compute a project budget."""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from .auth import service_token
from .config import settings


class PricingUnavailable(Exception):
    """pricing-service unreachable or returned an unexpected error."""


def quote_products(tier: str | None, items: list[dict]) -> dict:
    """Return {tier, lines, total} for a set of {product_id, qty}. Uses a service token."""
    url = f"{settings.pricing_url.rstrip('/')}{settings.api_prefix}/quote-products"
    body = json.dumps({"tier": tier, "items": items}).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {service_token()}"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8")[:150]
        except Exception:
            pass
        raise PricingUnavailable(f"pricing-service {e.code}: {detail}") from e
    except Exception as e:  # noqa: BLE001
        raise PricingUnavailable(f"pricing-service unreachable: {e}") from e
