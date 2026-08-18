"""Client for identity-service: create a consumer login on onboarding."""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from .auth import service_token
from .config import settings


class IdentityUnavailable(Exception):
    """identity-service unreachable, or user already exists."""


def create_consumer_user(email: str, name: str, org_ref: str, password: str) -> dict:
    """Provision a `consumer` login linked to the consumer record (org_ref). Uses a service token."""
    url = f"{settings.identity_url.rstrip('/')}{settings.api_prefix}/users"
    body = json.dumps({"email": email, "password": password, "name": name,
                       "role": "consumer", "org_ref": org_ref}).encode("utf-8")
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
        raise IdentityUnavailable(f"identity-service {e.code}: {detail}") from e
    except Exception as e:  # noqa: BLE001
        raise IdentityUnavailable(f"identity-service unreachable: {e}") from e
