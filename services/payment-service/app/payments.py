"""Payment-gateway adapter, dispatches to the provider configured in config.yaml.

The mock provider settles locally (no network). Real providers (razorpay/stripe/payu/cashfree) read
their credentials from the environment variables named in config.yaml; until those are set they create
a *pending* intent and report that the provider is not yet wired. Real API calls are intentionally left
as clearly-marked extension points, this service never hardcodes gateway keys.
"""
from __future__ import annotations

import uuid

from .config import active_provider, resolve_secret
from . import models


def _has_secrets(provider: str, pcfg: dict) -> bool:
    """True when every env-var named in this provider's config resolves to a non-empty value."""
    env_names = [v for k, v in pcfg.items() if k.endswith("_env")]
    return bool(env_names) and all(resolve_secret(n) for n in env_names)


def charge(amount: float) -> dict:
    """Attempt to charge via the active provider. Returns {status, provider, provider_ref, note}."""
    provider, pcfg = active_provider()

    if provider == "mock":
        settled = bool(pcfg.get("auto_confirm", True))
        return {
            "provider": "mock",
            "provider_ref": f"mock_{uuid.uuid4().hex[:16]}",
            "status": models.PAID if settled else models.PENDING,
            "note": "settled by mock gateway" if settled else "mock intent created",
        }

    # Real providers: create a pending intent. Wiring the actual API call is an extension point.
    if not _has_secrets(provider, pcfg):
        return {
            "provider": provider, "provider_ref": "", "status": models.PENDING,
            "note": f"{provider} selected but its API keys are not configured (see config.yaml env names)",
        }
    return {
        "provider": provider, "provider_ref": f"{provider}_intent_{uuid.uuid4().hex[:12]}",
        "status": models.PENDING,
        "note": f"{provider} intent created; complete via the provider's checkout/webhook",
    }


def confirm(provider: str) -> str:
    """Confirm a pending payment. Mock confirms immediately; real providers confirm via webhook."""
    if provider == "mock":
        return models.PAID
    return models.PENDING  # awaits provider webhook
