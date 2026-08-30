"""Procurement engine, Hub LLM analysis, and procurement orders."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import llm, orders, pricing_client, procurement_engine, schemas, service, site_client
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
    a reference lens, computed against the hub's LIST price (pricing-service, no tier) unless explicit
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
    # Use a demanded product name as the scout query when given (e.g. 'JSW Neosteel TMT bars'), so an
    # unavailable branded item still pulls relevant open-market offers for its material.
    scout_name = {}
    for d in demand:
        mid = d["material_id"]
        if d.get("product_name") and mid not in scout_name:
            scout_name[mid] = d["product_name"]
    for mid in {d["material_id"] for d in demand}:
        if refresh or not service.list_external_offers(db, mid):
            try:
                scouted.append(service.run_scout(db, mid, scout_name.get(mid, mid)))
            except Exception as e:  # noqa: BLE001, scouting is best-effort, never blocks the plan
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


_BOM_OPT_SCHEMA = (
    "You are a Bill-of-Materials optimizer for a construction-materials hub. You are given the current "
    "BOM (product lines with whole-project quantities), the available product catalog (branded SKUs "
    "under each material), and the hub user's instruction. Propose an optimized BOM. Output STRICT JSON "
    "only: {\"summary\": string, \"lines\": [{\"product_id\": string, \"product_name\": string, "
    "\"material_id\": string, \"total_qty\": number, \"reason\": string}]}.\n"
    "Rules: use ONLY product_id values that appear in the provided catalog; keep each material's total "
    "quantity close to the current BOM unless the instruction changes it; 'optimize cost' picks the "
    "cheaper/value brands, 'use premium' swaps to premium brands, quantity instructions adjust totals. "
    "Preserve the materials the project needs. If the current BOM is empty, propose a sensible starter "
    "BOM from the catalog per the instruction. The hub user reviews and edits your suggestion, so make it "
    "concrete and grounded in the catalog. Output JSON only."
)


_BOM_EXTRACT_SCHEMA = (
    "You extract a construction Bill of Materials from a raw document and map each item to the hub's "
    "product catalog. You are given the document text and the catalog (branded SKUs under materials). "
    "Output STRICT JSON only: {\"summary\": string, \"lines\": [{\"product_id\": string, "
    "\"product_name\": string, \"material_id\": string, \"total_qty\": number, \"phase_seq\": number, "
    "\"matched\": boolean, \"raw\": string}]}.\n"
    "Rules: for each material line in the document, pick the best-matching catalog product and use its "
    "product_id/material_id (matched=true). If nothing matches well, set product_id='' and matched=false "
    "and keep the document's wording in product_name and raw so the user can add the product. total_qty "
    "is the quantity from the document (whole-project). phase_seq: if the document assigns the item to a "
    "construction phase (1-9), use it; otherwise 0. Do not invent items not in the document. Output JSON only."
)


@router.post("/procurement/bom-extract")
async def bom_extract(file: UploadFile = File(...)):
    """Parse an uploaded BOM (pdf/docx/txt) and let the Hub LLM extract + map lines to catalog products."""
    from .. import catalog_client, doc_parse
    data = await file.read()
    text = doc_parse.extract_text(file.filename or "", data)[:8000]
    if not text.strip():
        return {"summary": "Could not read any text from the document.", "lines": []}
    try:
        catalog = [{k: p.get(k) for k in ("id", "name", "brand", "material_id", "grade")}
                   for p in catalog_client.list_products()]
    except Exception:  # noqa: BLE001
        catalog = []
    import json as _json
    result = llm.complete_json(_BOM_EXTRACT_SCHEMA, _json.dumps({"document": text, "catalog": catalog}))
    return result or {"summary": "Hub LLM unavailable - configure AI_PROVIDER.", "lines": []}


# BOM optimize / find-alternatives is advisory (read-only suggestion) - the spoke + SE use it too.
BOM_SUGGEST = require_role("spokesperson", "site_engineer", "architect", "hub_supervisor", "hub_manager")
# Field roles see the hub's SELLING price for stocked catalog products, but NEVER a market price
# (they request the price / order the market find through a BOQ order-request instead).
_FIELD_ROLES = {"spokesperson", "site_engineer", "architect", "finance"}


@router.post("/procurement/bom-optimize", dependencies=[Depends(BOM_SUGGEST)])
def bom_optimize(body: schemas.BomOptimizeIn, refresh: bool = False,
                 user: dict = Depends(current_user), db: Session = Depends(get_db)):
    """Find BOM alternatives: the Hub LLM suggests cheaper/alternative catalog products (priced at the
    hub's selling price), and the price-scout adds live open-market finds per material. Field roles see
    the hub selling price for stocked products but not market prices - they request/order those."""
    import json as _json
    field = user.get("role") in _FIELD_ROLES
    result = llm.complete_json(_BOM_OPT_SCHEMA, _json.dumps({
        "instruction": body.prompt, "current_bom": body.current_bom, "catalog": body.catalog,
    })) or {"summary": "Hub LLM unavailable - configure AI_PROVIDER.", "lines": []}
    # Enrich catalog suggestions with the hub SELLING price (never cost) so the field can compare.
    lines = result.get("lines") or []
    prices = pricing_client.product_selling_prices([l.get("product_id") for l in lines if isinstance(l, dict)])
    for l in lines:
        if isinstance(l, dict) and l.get("product_id") in prices:
            l["hub_price"] = prices[l["product_id"]]
            l["in_inventory"] = True
    # Live open-market alternatives via the scout (reuses SCOUT_API_KEY / Tavily) for each material.
    mats = {l.get("material_id") for l in (body.current_bom or []) if isinstance(l, dict) and l.get("material_id")}
    market = {}
    for mid in mats:
        offers = service.list_external_offers(db, mid)
        if refresh or not offers:
            try:
                service.run_scout(db, mid, mid)
            except Exception as e:  # noqa: BLE001, scouting is best-effort
                print(f"[bom-optimize] scout failed for {mid}: {type(e).__name__}: {e}", flush=True)
            offers = service.list_external_offers(db, mid)
        if offers:
            rows = []
            for o in offers[:5]:
                row = {"seller": o.seller, "product": o.product_name, "material_id": mid,
                       "source": o.source, "confidence": o.confidence}
                if field:
                    row["price_hidden"] = True   # the field requests the price / orders it, never sees it
                else:
                    row["price"] = float(o.price)
                    row["url"] = o.url
                rows.append(row)
            market[mid] = rows
    result["market"] = market
    result["field_view"] = field
    return result


# Spoke stock-order requests: the spoke requests, the hub approves (setting vendor + rate) -> PO.
REQUESTER = require_role("spokesperson", "site_engineer", "architect", "finance")


@router.post("/procurement/order-requests", response_model=schemas.OrderRequestOut, status_code=201,
             dependencies=[Depends(REQUESTER)])
def create_order_request(body: schemas.OrderRequestIn, user: dict = Depends(current_user),
                         db: Session = Depends(get_db)):
    """A spoke asks the hub to procure stock (optionally tied to a project); needs hub approval."""
    req = _run(service.create_order_request, db=db, requested_by=user.get("name", ""),
               requested_by_role=user.get("role", ""), site_ref=body.site_ref, note=body.note,
               lines=[l.model_dump() for l in body.lines])
    site_client.notify(req.site_ref, "order_request",
                       f"{req.code}: {len(req.lines)} item(s) requested by {req.requested_by_role or 'the field'}, "
                       "awaiting procurement approval.", audience="all")
    return req


@router.get("/procurement/order-requests", response_model=list[schemas.OrderRequestOut])
def list_order_requests(status: str | None = None, db: Session = Depends(get_db)):
    return service.list_order_requests(db, status)


@router.post("/procurement/order-requests/{req_id}/decide", response_model=schemas.OrderRequestOut,
             dependencies=[Depends(HUB_WRITE)])
def decide_order_request(req_id: int, body: schemas.OrderRequestDecideIn,
                         user: dict = Depends(current_user), db: Session = Depends(get_db)):
    """Hub approves (choosing a vendor + per-product rate -> creates a PO) or rejects the request."""
    req = _run(service.decide_order_request, db=db, req_id=req_id, approve=body.approve,
               vendor_id=body.vendor_id, prices=[p.model_dump() for p in body.prices],
               decided_by=user.get("name", ""))
    if req.status == "approved":
        site_client.notify(req.site_ref, "order_approved",
                           f"{req.code} approved by the hub; a purchase order was placed.", audience="all")
    elif req.status == "rejected":
        site_client.notify(req.site_ref, "order_rejected", f"{req.code} was declined by the hub.", audience="all")
    return req


@router.post("/procurement/boq-estimate")
def boq_estimate(body: schemas.BoqEstimateIn):
    """Second BOQ from the external estimator (stub by default), used to cross-check the SE's BOQ."""
    from .. import boq_estimator
    return boq_estimator.estimate([l.model_dump() for l in body.lines])


@router.post("/procurement/scout", dependencies=[Depends(HUB_WRITE)])
def scout(body: schemas.ScoutIn, db: Session = Depends(get_db)):
    """Pull indicative external market prices for a material (advisory market intelligence)."""
    return service.run_scout(db, body.material_id, body.material_name)


@router.get("/external-offers", response_model=list[schemas.ExternalOfferOut])
def external_offers(material_id: str | None = None, db: Session = Depends(get_db)):
    return service.list_external_offers(db, material_id)


# ---- Open-market watch: price drops + alerts ----

@router.get("/market/index")
def market_index(db: Session = Depends(get_db)):
    """Per-material daily market movement + up/down/stable outlook (feeds the hub dashboard widgets)."""
    from datetime import date
    return service.market_index(db, date.today())


@router.get("/market/price-drops")
def price_drops(db: Session = Depends(get_db)):
    """Products whose hub avg cost is beaten by a cheaper open-market offer (same category)."""
    return service.price_drops(db)


@router.post("/market/scan", dependencies=[Depends(HUB_WRITE)])
def market_scan(body: schemas.ScanIn, db: Session = Depends(get_db)):
    """Refresh open-market offers by scouting a category (or all). Also runs every 4h in the background."""
    from .. import catalog_client
    if body.category:
        mats = [body.category]
    else:
        try:
            mats = sorted({p["material_id"] for p in catalog_client.list_products()})
        except Exception:  # noqa: BLE001
            mats = ["cement", "steel", "sand", "aggregate", "bricks"]
    return service.scan_markets(db, mats)


@router.get("/market/alerts")
def list_alerts(db: Session = Depends(get_db)):
    """Active alerts with the offers currently matching each."""
    return service.evaluate_alerts(db)


@router.post("/market/alerts", status_code=201)
def create_alert(body: schemas.AlertIn, db: Session = Depends(get_db)):
    a = _run(service.create_alert, db=db, material_id=body.material_id, query=body.query, op=body.op,
             value=body.value, seller=body.seller, location=body.location)
    return {"id": a.id}


@router.delete("/market/alerts/{alert_id}", status_code=204)
def delete_alert(alert_id: int, db: Session = Depends(get_db)):
    service.delete_alert(db, alert_id)


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
