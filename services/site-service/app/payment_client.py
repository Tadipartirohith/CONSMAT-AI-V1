"""Client for payment-service: release held escrow as deliveries are confirmed."""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from .auth import service_token
from .config import settings


class PaymentUnavailable(Exception):
    """payment-service unreachable or returned an unexpected error."""


def project_paid(ref: str) -> bool:
    """True if the project (ref = SITE-code) has a captured payment (held/paid/released)."""
    url = f"{settings.payment_url.rstrip('/')}{settings.api_prefix}/payments?ref={ref}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {service_token()}"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            rows = json.loads(resp.read().decode("utf-8"))
        return any(p.get("status") in ("held", "paid", "released") for p in rows)
    except Exception:  # noqa: BLE001, treat unknown as not-yet-paid
        return False


def release_escrow(ref: str, fraction: float) -> dict:
    """Release escrow for a project ref up to `fraction` (0..1) of each held payment. Uses a service token."""
    url = f"{settings.payment_url.rstrip('/')}{settings.api_prefix}/payments/release"
    body = json.dumps({"ref": ref, "fraction": fraction}).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {service_token()}"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8")[:150]
        except Exception:
            pass
        raise PaymentUnavailable(f"payment-service {e.code}: {detail}") from e
    except Exception as e:  # noqa: BLE001
        raise PaymentUnavailable(f"payment-service unreachable: {e}") from e
