"""Client for inventory-service: catalog + landed cost (avg_cost)."""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from .auth import service_token
from .config import settings


class InventoryUnavailable(Exception):
    """inventory-service unreachable or returned an unexpected error."""


def _base() -> str:
    return f"{settings.inventory_url.rstrip('/')}{settings.api_prefix}"


def _get(url: str):
    try:
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {service_token()}"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise InventoryUnavailable(f"inventory-service {e.code}") from e
    except Exception as e:  # noqa: BLE001
        raise InventoryUnavailable(f"inventory-service unreachable: {e}") from e


def landed_cost(material_id: str) -> float:
    """Current per-unit landed cost = inventory weighted-average cost (0 if no stock)."""
    data = _get(f"{_base()}/inventory/{material_id}")
    return float(data["avg_cost"]) if data else 0.0


def material_ids() -> list[str]:
    data = _get(f"{_base()}/materials") or []
    return [m["id"] for m in data]
