"""Price-scout — pull indicative external market prices as advisory offers.

Providers (config `SCOUT_PROVIDER`):
  - `auto`  : use `llm` if the Hub LLM is configured, else `stub`.
  - `llm`   : ask the Hub LLM for *indicative* current market prices from Indian B2B suppliers
              (IndiaMART / TradeIndia style). These are ESTIMATES from the model, not live quotes.
  - `stub`  : a small curated offline set (for demo / no-key).
  - `serpapi` / real web search : extension point (needs a search API key) — not wired here.

External offers are **advisory only** — the deterministic buy plan still uses the registered vendor
registry. The hub can onboard a promising external offer as a real vendor price. There is intentionally
NO IndiaMART scraper: no clean price API + ToS/anti-bot make it a fragile foundation.
"""
from __future__ import annotations

from . import llm
from .config import settings

_SCOUT_SCHEMA = (
    "You are a procurement market analyst for a construction-materials hub in Hyderabad, India. Given a "
    "material and known brands, return INDICATIVE current market prices (INR) as might be seen on Indian "
    "B2B marketplaces (IndiaMART, TradeIndia) or from manufacturers/distributors. These are estimates, "
    "not live quotes. Output STRICT JSON only: {\"offers\": [{\"seller\": string, \"product\": string, "
    "\"price\": number (INR per the material's usual unit), \"url\": string (a plausible marketplace/"
    "manufacturer URL), \"note\": string}]}. Return 3-6 realistic offers. Do not invent absurd prices."
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
        return "llm" if llm.is_configured() else "stub"
    return p


def scout(material_id: str, material_name: str = "", brands: list[str] | None = None) -> tuple[list[dict], str]:
    """Return (offers, provider). Each offer: {seller, product_name, price, url, note}."""
    provider = _provider()
    if provider == "llm":
        result = llm.complete_json(_SCOUT_SCHEMA, __import__("json").dumps(
            {"material": material_name or material_id, "known_brands": brands or []}))
        if result and isinstance(result.get("offers"), list):
            out = []
            for o in result["offers"]:
                try:
                    out.append({"seller": str(o.get("seller", ""))[:160],
                                "product_name": str(o.get("product", ""))[:200],
                                "price": float(o["price"]), "url": str(o.get("url", ""))[:300],
                                "note": str(o.get("note", ""))[:255]})
                except (KeyError, TypeError, ValueError):
                    continue
            if out:
                return out, "llm"
        # fall through to stub on any LLM failure
    stub = [{"seller": o["seller"], "product_name": o["product"], "price": float(o["price"]),
             "url": o["url"], "note": o["note"]} for o in _STUB.get(material_id, [])]
    return stub, "stub"
