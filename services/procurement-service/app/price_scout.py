"""Price-scout — pull external market prices as advisory offers.

Providers (config `SCOUT_PROVIDER`):
  - `auto`  : `web` if a Gemini key is configured (live Google-Search grounding), else `llm` if any
              Hub LLM is configured, else `stub`.
  - `web`   : Gemini with **live Google Search grounding** — the model actually searches the internet
              (IndiaMART / TradeIndia / manufacturer sites) and returns grounded current prices with
              real source URLs. Prices are still treated as INDICATIVE (public listings, not a firm
              quote to us) but they are real, cited numbers rather than the model's guess.
  - `llm`   : ask the Hub LLM for *indicative* market prices from memory (no live search). Estimates.
  - `stub`  : a small curated offline set (for demo / no-key).

External offers are **advisory only** — the deterministic buy plan still uses the registered vendor
registry. The hub can onboard a promising external offer as a real vendor price. There is intentionally
NO bespoke IndiaMART scraper: no clean price API + ToS/anti-bot make it a fragile foundation; live
Google-Search grounding is the sanctioned way to reach the open web.
"""
from __future__ import annotations

import json
import re
import urllib.request

from . import llm
from .config import settings

_UNIT_HINT = {
    "cement": "INR per 50kg bag", "steel": "INR per tonne", "sand": "INR per tonne",
    "aggregate": "INR per tonne", "bricks": "INR per piece",
}

_SCOUT_SCHEMA = (
    "You are a procurement market analyst for a construction-materials hub in Hyderabad, India. Given a "
    "material and known brands, return INDICATIVE current market prices (INR) as might be seen on Indian "
    "B2B marketplaces (IndiaMART, TradeIndia) or from manufacturers/distributors. These are estimates, "
    "not live quotes. Output STRICT JSON only: {\"offers\": [{\"seller\": string, \"product\": string, "
    "\"price\": number (INR per the material's usual unit), \"url\": string (a plausible marketplace/"
    "manufacturer URL), \"note\": string}]}. Return 3-6 realistic offers. Do not invent absurd prices."
)

_WEB_PROMPT = (
    "Search the web for CURRENT wholesale/dealer prices in India (prefer Hyderabad / Telangana) for the "
    "construction material below. Use IndiaMART, TradeIndia, manufacturer and dealer listings. Report {unit}. "
    "Material: {material}. Known brands to prioritise: {brands}.\n"
    "Return ONLY a JSON object, no prose, no markdown fences:\n"
    "{{\"offers\": [{{\"seller\": string, \"product\": string, \"price\": number, \"url\": string "
    "(the real source listing URL), \"note\": string (e.g. min order, location)}}]}}\n"
    "Give 3-6 grounded offers with real numbers and real source URLs. Omit any offer you cannot price."
)

# Curated offline fallback (per material). Clearly indicative.
_STUB = {
    "cement": [
        {"seller": "Shree Cement Dealer (IndiaMART)", "product": "Shree Jung Rodhak PPC 50kg", "price": 360, "url": "https://www.indiamart.com/", "note": "bulk quote"},
        {"seller": "Penna Cement Distributor", "product": "Penna OPC 53 50kg", "price": 372, "url": "https://www.indiamart.com/", "note": "min 500 bags"},
    ],
    "steel": [
        {"seller": "Kamdhenu Steel (TradeIndia)", "product": "Kamdhenu Fe 550D TMT", "price": 61500, "url": "https://www.tradeindia.com/", "note": "ex-works"},
    ],
    "sand": [{"seller": "Local M-Sand Supplier", "product": "M-Sand (concrete)", "price": 1020, "url": "https://www.indiamart.com/", "note": "per tonne"}],
    "aggregate": [{"seller": "Quarry Direct", "product": "20mm Aggregate", "price": 960, "url": "https://www.indiamart.com/", "note": "per tonne"}],
    "bricks": [{"seller": "AAC Block Mfr", "product": "AAC Block 600x200x100", "price": 42, "url": "https://www.indiamart.com/", "note": "per pc"}],
}


def _provider() -> str:
    p = settings.scout_provider.lower()
    if p == "auto":
        if settings.ai_provider.lower() == "gemini" and settings.ai_api_key:
            return "web"
        return "llm" if llm.is_configured() else "stub"
    return p


def _coerce(offers: list) -> list[dict]:
    out = []
    for o in offers or []:
        try:
            out.append({"seller": str(o.get("seller", ""))[:160],
                        "product_name": str(o.get("product", o.get("product_name", "")))[:200],
                        "price": float(o["price"]), "url": str(o.get("url", ""))[:300],
                        "note": str(o.get("note", ""))[:255]})
        except (KeyError, TypeError, ValueError):
            continue
    return out


def _extract_json(text: str) -> dict | None:
    """Grounded responses may wrap JSON in prose/markdown — pull the first {...} object out."""
    if not text:
        return None
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def _gemini_grounded(material_name: str, brands: list[str], unit: str) -> list[dict]:
    """Live Google-Search grounded price lookup via Gemini's native generateContent endpoint."""
    key = settings.ai_api_key
    model = (settings.ai_model.strip() or "gemini-flash-lite-latest")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    prompt = _WEB_PROMPT.format(unit=unit, material=material_name,
                                brands=", ".join(brands) if brands else "any reputable brand")
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {"temperature": 0},
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=40) as resp:
        j = json.loads(resp.read().decode("utf-8"))
    parts = j.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts)
    parsed = _extract_json(text)
    return _coerce(parsed.get("offers")) if parsed else []


def scout(material_id: str, material_name: str = "", brands: list[str] | None = None) -> tuple[list[dict], str]:
    """Return (offers, provider). Each offer: {seller, product_name, price, url, note}.

    provider is one of: web (live grounded search), llm (model estimate), stub (offline curated).
    """
    provider = _provider()
    name = material_name or material_id
    unit = _UNIT_HINT.get(material_id, "INR per usual unit")

    if provider == "web":
        try:
            offers = _gemini_grounded(name, brands or [], unit)
            if offers:
                return offers, "web"
        except Exception as e:  # noqa: BLE001 — degrade to estimate/stub on any grounding failure
            body = ""
            try:
                body = e.read().decode("utf-8")[:300]  # type: ignore[attr-defined]
            except Exception:
                pass
            print(f"[price-scout] web grounding failed: {type(e).__name__}: {e} | {body}", flush=True)
        provider = "llm" if llm.is_configured() else "stub"  # fall through

    if provider == "llm":
        result = llm.complete_json(_SCOUT_SCHEMA, json.dumps(
            {"material": name, "known_brands": brands or []}))
        offers = _coerce(result.get("offers")) if result else []
        if offers:
            for o in offers:
                o["url"] = ""  # estimates are from memory — don't surface fabricated source links
            return offers, "llm"
        # fall through to stub on any LLM failure

    stub = [{"seller": o["seller"], "product_name": o["product"], "price": float(o["price"]),
             "url": o["url"], "note": o["note"]} for o in _STUB.get(material_id, [])]
    return stub, "stub"
