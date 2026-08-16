"""Client for inventory-service: catalog lookup + phase dispatch (outbound)."""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from .auth import service_token
from .config import settings


class InventoryUnavailable(Exception):
    """inventory-service unreachable or returned an unexpected error."""


class InsufficientStock(Exception):
    """inventory-service rejected an outbound because stock was insufficient (HTTP 409)."""


def _base() -> str:
    return f"{settings.inventory_url.rstrip('/')}{settings.api_prefix}"


def _auth() -> dict:
    return {"Authorization": f"Bearer {service_token()}"}


def get_materials() -> dict[str, float]:
    """Return {material_id: per_sqft} from the inventory-service catalog (Q11)."""
    url = f"{_base()}/materials"
    try:
        req = urllib.request.Request(url, headers=_auth())
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        raise InventoryUnavailable(f"catalog fetch failed: {e}") from e
    return {m["id"]: float(m.get("per_sqft") or 0) for m in data}


def _post(path: str, body: dict, *, insufficient_ref: str = "") -> dict:
    req = urllib.request.Request(f"{_base()}{path}", data=json.dumps(body).encode("utf-8"),
                                 method="POST", headers={"Content-Type": "application/json", **_auth()})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 409:
            raise InsufficientStock(insufficient_ref) from e
        detail = ""
        try:
            detail = e.read().decode("utf-8")[:200]
        except Exception:
            pass
        raise InventoryUnavailable(f"inventory-service {e.code}: {detail}") from e
    except Exception as e:  # noqa: BLE001
        raise InventoryUnavailable(f"inventory-service unreachable: {e}") from e


def post_outbound(material_id: str, qty: float, ref_id: str) -> dict:
    """Dispatch material-level stock hub → site (legacy path)."""
    return _post("/inventory/outbound",
                 {"material_id": material_id, "qty": qty, "ref_type": "dispatch", "ref_id": ref_id},
                 insufficient_ref=material_id)


def post_product_outbound(product_id: str, qty: float, ref_id: str, *, from_reservation: bool = False) -> dict:
    """Dispatch brand-level stock hub → site. Raises InsufficientStock on 409."""
    return _post("/inventory/product-outbound",
                 {"product_id": product_id, "qty": qty, "ref_type": "dispatch", "ref_id": ref_id,
                  "from_reservation": from_reservation},
                 insufficient_ref=product_id)


def post_product_reserve(product_id: str, qty: float, *, allow_over: bool = True) -> dict:
    """Reserve committed brand demand (best-effort; allows over-reservation for the 3x buffer)."""
    return _post("/inventory/product-reserve",
                 {"product_id": product_id, "qty": qty, "allow_over": allow_over})


def post_product_release(product_id: str, qty: float) -> dict:
    return _post("/inventory/product-release", {"product_id": product_id, "qty": qty})
