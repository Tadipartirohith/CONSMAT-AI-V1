"""Hub LLM — procurement intelligence (advice only).

Given a demand, the market prices, the deterministic cheapest-source plan, and (optionally) a
profitability breakdown, the LLM explains margins, flags risks, and suggests cheaper alternatives.
It NEVER computes or sets prices — every number is supplied by the deterministic engine. On any error
or when disabled (AI_PROVIDER=stub / no key) it returns None and callers fall back to the plan alone.

Pluggable provider, carried from V0: OpenAI-compatible (openai/gemini/groq/openrouter/openai-compat)
plus anthropic. Transport is the Python stdlib (no extra dependency).
"""
from __future__ import annotations

import json
import urllib.request

from .config import settings

# provider -> (default base URL, default model)
OPENAI_COMPAT = {
    "openai": ("https://api.openai.com/v1", "gpt-4o-mini"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "gemini-flash-lite-latest"),
    "groq": ("https://api.groq.com/openai/v1", "llama-3.3-70b-versatile"),
    "openrouter": ("https://openrouter.ai/api/v1", "meta-llama/llama-3.3-70b-instruct"),
    "openai-compat": ("", ""),
}

SCHEMA = (
    "You are the Hub's procurement analyst for a construction-materials distributor. You do NOT set "
    "or invent prices, costs, or margins — every figure is given to you by the system. Read the "
    "demand, the market prices per material (cheapest-first), the chosen cheapest-source plan, and the "
    "profitability breakdown if present. Output STRICT JSON only with keys:\n"
    "  summary: one or two sentences on the procurement plan. If some demand is 'unavailable' (no "
    "registry vendor prices that product/material), do NOT call it a failure — state plainly that those "
    "items have no vendor yet and can be procured once a vendor price is added or a stocked brand is chosen.\n"
    "  profitability_note: comment on margins (call out any loss-making or thin-margin materials). "
    "Empty string if no selling prices were given.\n"
    "  alternatives: array of {material_id, suggestion} — cheaper vendor mixes, substitute grades, or "
    "hub-self supply worth considering. Only concrete, grounded suggestions from the given data. If "
    "external_offers are present and materially cheaper than the chosen registry vendor, suggest "
    "onboarding that supplier — but treat 'indicative' external prices as estimates to verify, not firm.\n"
    "  flags: array of short risk strings (e.g. 'demand below vendor min order qty', 'single source').\n"
    "  recommendation: a one-line recommended action for the hub manager.\n"
    "Base everything strictly on the numbers provided. Output JSON only."
)


def _post_json(url: str, headers: dict, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST",
                                 headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def is_configured() -> bool:
    provider = settings.ai_provider.lower()
    return (provider in OPENAI_COMPAT and (settings.ai_api_key or provider == "openai-compat")) \
        or (provider == "anthropic" and settings.ai_api_key)


def complete_json(system_prompt: str, user_content: str) -> dict | None:
    """Reusable strict-JSON completion against the configured provider. None on any error/disabled."""
    provider = settings.ai_provider.lower()
    key = settings.ai_api_key
    if not is_configured():
        return None
    base_url = settings.ai_base_url.strip().rstrip("/")
    try:
        if provider in OPENAI_COMPAT:
            default_base, default_model = OPENAI_COMPAT[provider]
            base_url = base_url or default_base
            model = settings.ai_model.strip() or default_model
            headers = {"Authorization": f"Bearer {key}"} if key else {}
            j = _post_json(f"{base_url}/chat/completions", headers, {
                "model": model, "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [{"role": "system", "content": system_prompt},
                             {"role": "user", "content": user_content}],
            })
            content = j["choices"][0]["message"]["content"]
        else:  # anthropic
            model = settings.ai_model.strip() or "claude-3-5-haiku-latest"
            j = _post_json(f"{base_url or 'https://api.anthropic.com/v1'}/messages",
                           {"x-api-key": key, "anthropic-version": "2023-06-01"},
                           {"model": model, "max_tokens": 800, "system": system_prompt,
                            "messages": [{"role": "user", "content": user_content}]})
            content = j["content"][0]["text"]
        return json.loads(content)
    except Exception as e:  # noqa: BLE001 — any failure degrades gracefully
        body = ""
        try:
            body = e.read().decode("utf-8")[:400]  # type: ignore[attr-defined]
        except Exception:
            pass
        print(f"[hub-llm] ERROR: {type(e).__name__}: {e} | {body}", flush=True)
        return None


def analyze(context: dict) -> dict | None:
    """Return LLM advice for a procurement context, or None if disabled/errored."""
    return complete_json(SCHEMA, json.dumps(context))
