"""Client for site-service: post a notification when an order-request event happens.

Order requests can be tied to a project (site_ref = SITE-<id>). When they are, procurement posts a
notification to site-service so the field team sees the request / approval on the site and in the bell.
Best-effort: a notify failure never blocks the request flow.
"""
from __future__ import annotations

import json
import urllib.request

from .auth import service_token
from .config import settings


def notify(site_ref: str, kind: str, message: str, audience: str = "all") -> None:
    """POST an internal notification for SITE-<id>. No-op on any error or when site_ref is blank."""
    ref = (site_ref or "").strip()
    base = settings.site_url.rstrip("/")
    if not ref or not base:
        return
    url = f"{base}{settings.api_prefix}/internal/notify"
    data = json.dumps({"site_ref": ref, "kind": kind, "message": message, "audience": audience}).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {service_token()}"})
    try:
        urllib.request.urlopen(req, timeout=10).read()
    except Exception as e:  # noqa: BLE001, notifications must never block procurement
        print(f"[site-client] notify failed: {type(e).__name__}: {e}", flush=True)
