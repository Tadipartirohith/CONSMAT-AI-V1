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


def product_landed(product_id: str) -> dict:
    """Return {material_id, avg_cost} for a product. avg_cost is the brand's landed cost (0 if no stock);
    material_id comes from the catalog even when the product has never been stocked."""
    stock = _get(f"{_base()}/product-stock/{product_id}")
    if stock:
        return {"material_id": stock["material_id"], "avg_cost": float(stock["avg_cost"])}
    prod = _get(f"{_base()}/products/{product_id}")
    if prod is None:
        raise InventoryUnavailable(f"unknown product: {product_id}")
    return {"material_id": prod["material_id"], "avg_cost": 0.0}
