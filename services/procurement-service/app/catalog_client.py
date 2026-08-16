"""Client for the inventory-service catalog (products/materials)."""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from .auth import service_token
from .config import settings


class CatalogError(Exception):
    """Catalog unreachable or product not found."""


def get_product(product_id: str) -> dict | None:
    """Fetch a product from the catalog (to denormalize material/brand/name on set-price)."""
    url = f"{settings.inventory_url.rstrip('/')}{settings.api_prefix}/products/{product_id}"
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
