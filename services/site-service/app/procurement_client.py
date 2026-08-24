"""Client for procurement-service: the external second-BOQ estimator."""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from .auth import service_token
from .config import settings


class ProcurementUnavailable(Exception):
    """procurement-service unreachable or returned an unexpected error."""


def estimate_boq(lines: list[dict]) -> dict:
    """Get the external app's BOQ for the given CE BOQ lines. Uses a service token."""
    url = f"{settings.procurement_url.rstrip('/')}{settings.api_prefix}/procurement/boq-estimate"
    body = json.dumps({"lines": lines}).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {service_token()}"})
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8")[:150]
        except Exception:
            pass
        raise ProcurementUnavailable(f"procurement-service {e.code}: {detail}") from e
    except Exception as e:  # noqa: BLE001
        raise ProcurementUnavailable(f"procurement-service unreachable: {e}") from e
