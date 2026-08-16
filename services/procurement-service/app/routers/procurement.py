"""Procurement engine, Hub LLM analysis, and procurement orders."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import llm, orders, pricing_client, procurement_engine, schemas, service
from ..auth import current_user, require_role
from ..config import settings
from ..db import get_db

# Reads/analysis: any authenticated user. Order create/receive: hub staff.
HUB_WRITE = require_role("hub_supervisor", "hub_manager")
router = APIRouter(tags=["procurement"], dependencies=[Depends(current_user)])


def _run(fn, **kwargs):
    try:
        return fn(**kwargs)
    except service.ProcurementError as e:
        raise HTTPException(409, str(e))


@router.get("/procurement/llm-status")
def llm_status():
    """Whether the Hub LLM is live or on the deterministic stub."""
    provider = settings.ai_provider.lower()
    cloud = provider in ("openai", "anthropic", "gemini", "groq", "openrouter")
    live = (cloud and bool(settings.ai_api_key)) or provider == "openai-compat"
    return {"live": live, "mode": provider if live else "stub",
            "model": settings.ai_model or ("provider default" if live else None)}


@router.post("/procurement/plan")
def make_plan(body: schemas.PlanIn, db: Session = Depends(get_db)):
    """Deterministic cheapest-source plan (no LLM)."""
    demand = [d.model_dump() for d in body.demand]
    return procurement_engine.plan(db, demand)


@router.post("/procurement/analyze")
def analyze(body: schemas.AnalyzeIn, refresh: bool = False, db: Session = Depends(get_db)):
    """Deterministic plan + profitability, with optional Hub LLM advice layered on top.

    Procurement is tier-agnostic: it buys at the cheapest source regardless of consumer. Profitability is
    a reference lens — computed against the hub's LIST price (pricing-service, no tier) unless explicit
    `selling_prices` are supplied. The Hub pulls **live external market prices** (Google-Search grounded
    when a Gemini key is set) for every demanded material so the LLM can flag a cheaper source even when
    the registry / inventory already supplies it. Pass `?refresh=1` to force a fresh web scout."""
    demand = [d.model_dump() for d in body.demand]
    result = procurement_engine.plan(db, demand)
    selling = body.selling_prices
    price_source = "provided" if selling else None
    if selling is None:
        selling = pricing_client.selling_prices(None)  # list price (no tier)
        price_source = "list-price" if selling else "unavailable"
    profit = procurement_engine.profitability(result, selling)
    # Market context for the LLM (all vendors per material, not just the chosen one).
    market = {d["material_id"]: service.market_prices(db, d["material_id"]) for d in demand}
    # Live external market intelligence: scout the open web for each material if we have nothing cached
    # (or on ?refresh=1). Grounded offers become advisory alternatives the LLM compares against.
    scouted = []
    for mid in {d["material_id"] for d in demand}:
        if refresh or not service.list_external_offers(db, mid):
            try:
                scouted.append(service.run_scout(db, mid, mid))
            except Exception as e:  # noqa: BLE001 — scouting is best-effort, never blocks the plan
                print(f"[analyze] scout failed for {mid}: {type(e).__name__}: {e}", flush=True)
    external = {}
    for mid in {d["material_id"] for d in demand}:
        offers = service.list_external_offers(db, mid)
        if offers:
            external[mid] = [
                {"seller": o.seller, "product": o.product_name, "price": float(o.price), "url": o.url,
                 "source": o.source, "confidence": o.confidence} for o in offers]
    advice = llm.analyze({
        "demand": demand, "plan": result, "profitability": profit, "market": market,
        "external_offers": external,
    })
    return {
        "plan": result,
        "profitability": profit,
        "price_source": price_source,
        "advice": advice,
        "engine": "llm" if advice is not None else "deterministic",
    }


@router.post("/procurement/orders", response_model=schemas.OrderOut, status_code=201, dependencies=[Depends(HUB_WRITE)])
def create_order(body: schemas.OrderIn, db: Session = Depends(get_db)):
    return _run(orders.create_order, db=db, lines=[l.model_dump() for l in body.lines], note=body.note)


@router.post("/procurement/scout", dependencies=[Depends(HUB_WRITE)])
def scout(body: schemas.ScoutIn, db: Session = Depends(get_db)):
    """Pull indicative external market prices for a material (advisory market intelligence)."""
    return service.run_scout(db, body.material_id, body.material_name)


@router.get("/external-offers", response_model=list[schemas.ExternalOfferOut])
def external_offers(material_id: str | None = None, db: Session = Depends(get_db)):
    return service.list_external_offers(db, material_id)


@router.post("/external-offers/import", dependencies=[Depends(HUB_WRITE)])
def import_offers(body: schemas.ImportIn, db: Session = Depends(get_db)):
    """Ingest a supplier price list (firm external offers, e.g. from CSV)."""
    n = service.import_offers(db, [o.model_dump() for o in body.offers])
    return {"imported": n}


@router.get("/procurement/orders", response_model=list[schemas.OrderOut])
def list_orders(status: str | None = None, db: Session = Depends(get_db)):
    return orders.list_orders(db, status)


@router.get("/procurement/orders/{order_id}", response_model=schemas.OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db)):
    o = orders.get_order(db, order_id)
    if o is None:
        raise HTTPException(404, f"Unknown order: PO-{order_id}")
    return o


@router.post("/procurement/orders/{order_id}/receive", response_model=schemas.OrderOut, dependencies=[Depends(HUB_WRITE)])
def receive_order(order_id: int, db: Session = Depends(get_db)):
    """Post each line to inventory-service as an inbound receipt, then mark received."""
    return _run(orders.receive_order, db=db, order_id=order_id)
