"""Client for inventory-service: catalog lookup + phase dispatch (outbound)."""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from .config import settings


class InventoryUnavailable(Exception):
    """inventory-service unreachable or returned an unexpected error."""


class InsufficientStock(Exception):
    """inventory-service rejected an outbound because stock was insufficient (HTTP 409)."""


def _base() -> str:
    return f"{settings.inventory_url.rstrip('/')}{settings.api_prefix}"


def get_materials() -> dict[str, float]:
    """Return {material_id: per_sqft} from the inventory-service catalog (Q11)."""
    url = f"{_base()}/materials"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        raise InventoryUnavailable(f"catalog fetch failed: {e}") from e
    return {m["id"]: float(m.get("per_sqft") or 0) for m in data}


def post_outbound(material_id: str, qty: float, ref_id: str) -> dict:
    """Dispatch stock hub → site. Raises InsufficientStock on 409, InventoryUnavailable otherwise."""
    url = f"{_base()}/inventory/outbound"
    payload = json.dumps({
        "material_id": material_id, "qty": qty, "ref_type": "dispatch", "ref_id": ref_id,
    }).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 409:
            raise InsufficientStock(material_id) from e
        detail = ""
        try:
            detail = e.read().decode("utf-8")[:200]
        except Exception:
            pass
        raise InventoryUnavailable(f"inventory-service {e.code}: {detail}") from e
    except Exception as e:  # noqa: BLE001
        raise InventoryUnavailable(f"inventory-service unreachable: {e}") from e
