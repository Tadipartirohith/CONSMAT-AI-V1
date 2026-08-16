"""Procurement engine, Hub LLM analysis, and procurement orders."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import llm, orders, procurement_engine, schemas, service
from ..config import settings
from ..db import get_db

router = APIRouter(tags=["procurement"])


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
def analyze(body: schemas.AnalyzeIn, db: Session = Depends(get_db)):
    """Deterministic plan + profitability, with optional Hub LLM advice layered on top."""
    demand = [d.model_dump() for d in body.demand]
    result = procurement_engine.plan(db, demand)
    profit = procurement_engine.profitability(result, body.selling_prices)
    # Market context for the LLM (all vendors per material, not just the chosen one).
    market = {d["material_id"]: service.market_prices(db, d["material_id"]) for d in demand}
    advice = llm.analyze({
        "demand": demand, "plan": result, "profitability": profit, "market": market,
    })
    return {
        "plan": result,
        "profitability": profit,
        "advice": advice,
        "engine": "llm" if advice is not None else "deterministic",
    }


@router.post("/procurement/orders", response_model=schemas.OrderOut, status_code=201)
def create_order(body: schemas.OrderIn, db: Session = Depends(get_db)):
    return _run(orders.create_order, db=db, lines=[l.model_dump() for l in body.lines], note=body.note)


@router.get("/procurement/orders", response_model=list[schemas.OrderOut])
def list_orders(status: str | None = None, db: Session = Depends(get_db)):
    return orders.list_orders(db, status)


@router.get("/procurement/orders/{order_id}", response_model=schemas.OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db)):
    o = orders.get_order(db, order_id)
    if o is None:
        raise HTTPException(404, f"Unknown order: PO-{order_id}")
    return o


@router.post("/procurement/orders/{order_id}/receive", response_model=schemas.OrderOut)
def receive_order(order_id: int, db: Session = Depends(get_db)):
    """Post each line to inventory-service as an inbound receipt, then mark received."""
    return _run(orders.receive_order, db=db, order_id=order_id)
