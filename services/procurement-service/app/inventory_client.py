"""Minimal client for inventory-service (synchronous REST, D10). Uses stdlib urllib."""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from .config import settings


class InventoryUnavailable(Exception):
    """Raised when inventory-service cannot be reached or rejects a call."""


def post_inbound(material_id: str, qty: float, unit_cost: float, ref_id: str) -> dict:
    """Receive procured stock into the hub inventory (inbound ledger entry)."""
    url = f"{settings.inventory_url.rstrip('/')}{settings.api_prefix}/inventory/inbound"
    payload = json.dumps({
        "material_id": material_id, "qty": qty, "unit_cost": unit_cost,
        "ref_type": "procurement", "ref_id": ref_id,
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8")[:200]
        except Exception:
            pass
        raise InventoryUnavailable(f"inventory-service {e.code}: {detail}") from e
    except Exception as e:  # noqa: BLE001
        raise InventoryUnavailable(f"inventory-service unreachable: {e}") from e
