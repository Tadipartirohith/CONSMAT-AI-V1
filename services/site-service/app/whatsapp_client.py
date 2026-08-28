"""WhatsApp notifications for the customer (pluggable, best-effort).

Stub by default: it logs the message so the flow is visible without a real integration. Set
`WHATSAPP_PROVIDER=meta` plus `WHATSAPP_TOKEN` and `WHATSAPP_PHONE_ID` (Meta WhatsApp Cloud API) to send
for real. Tokens come from the environment - this service never hardcodes them.
"""
from __future__ import annotations

import json
import urllib.request

from .config import settings


def notify(to_phone: str, text: str) -> dict:
    provider = (settings.whatsapp_provider or "stub").lower()
    to = "".join(ch for ch in (to_phone or "") if ch.isdigit())
    if not to:
        return {"provider": provider, "sent": False, "reason": "no phone"}
    if provider == "meta" and settings.whatsapp_token and settings.whatsapp_phone_id:
        try:  # extension point: Meta WhatsApp Cloud API
            url = f"https://graph.facebook.com/v20.0/{settings.whatsapp_phone_id}/messages"
            payload = {"messaging_product": "whatsapp", "to": to, "type": "text",
                       "text": {"body": text[:1000]}}
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), method="POST",
                                         headers={"Content-Type": "application/json",
                                                  "Authorization": f"Bearer {settings.whatsapp_token}"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                json.loads(resp.read().decode("utf-8"))
            return {"provider": "meta", "sent": True}
        except Exception as e:  # noqa: BLE001, best-effort
            print(f"[whatsapp] meta send failed: {type(e).__name__}: {e}", flush=True)
            return {"provider": "meta", "sent": False, "error": str(e)}
    print(f"[whatsapp:stub] to +{to}: {text}", flush=True)
    return {"provider": "stub", "sent": False, "logged": True}
