"""Client for the inventory-service catalog (products/materials)."""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from .auth import service_token
from .config import settings


class CatalogError(Exception):
    """Catalog unreachable or product not found."""


def _get(path: str):
    url = f"{settings.inventory_url.rstrip('/')}{settings.api_prefix}{path}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {service_token()}"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise CatalogError(f"catalog {e.code}") from e
    except Exception as e:  # noqa: BLE001
        raise CatalogError(f"catalog unreachable: {e}") from e


def get_product(product_id: str) -> dict | None:
    """Fetch a product from the catalog (to denormalize material/brand/name on set-price)."""
    return _get(f"/products/{product_id}")


def list_products() -> list[dict]:
    return _get("/products") or []


def list_materials() -> list[dict]:
    """All catalog materials (id, name, segment, category, unit, per_sqft)."""
    return _get("/materials") or []


def list_product_stock() -> list[dict]:
    """All brand-level stock positions (product_id, material_id, on_hand, reserved, avg_cost)."""
    return _get("/product-stock") or []
