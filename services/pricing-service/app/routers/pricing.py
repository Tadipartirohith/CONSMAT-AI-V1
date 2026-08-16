"""Pricing REST API: margin rules + selling-price computation."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import inventory_client, schemas, service
from ..auth import current_user, require_role
from ..db import get_db

# Reads (price/quote/selling-prices): any authenticated user or internal service.
# Margin-rule changes: hub manager only (the hub sets the price).
MANAGER = require_role("hub_manager")
router = APIRouter(tags=["pricing"], dependencies=[Depends(current_user)])


def _run(fn, **kwargs):
    try:
        return fn(**kwargs)
    except service.PricingError as e:
        raise HTTPException(409, str(e))
    except inventory_client.InventoryUnavailable as e:
        raise HTTPException(502, f"inventory-service error: {e}")


# ---- margin rules ----
@router.get("/margins", response_model=list[schemas.RuleOut])
def list_rules(db: Session = Depends(get_db)):
    return service.list_rules(db)


@router.put("/margins", response_model=schemas.RuleOut, dependencies=[Depends(MANAGER)])
def set_rule(body: schemas.RuleIn, db: Session = Depends(get_db)):
    return _run(service.set_rule, db=db, material_id=body.material_id, tier=body.tier,
                margin_pct=body.margin_pct)


@router.delete("/margins/{rule_id}", status_code=204, dependencies=[Depends(MANAGER)])
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    _run(service.delete_rule, db=db, rule_id=rule_id)


# ---- pricing ----
@router.get("/price/{material_id}", response_model=schemas.PriceOut)
def price(material_id: str, tier: str | None = None, db: Session = Depends(get_db)):
    """Selling price per unit for a material at a consumer tier."""
    return _run(service.price_material, db=db, material_id=material_id, tier=tier)


@router.post("/quote")
def quote(body: schemas.QuoteIn, db: Session = Depends(get_db)):
    """Priced quote for a set of materials + quantities at a tier."""
    return _run(service.quote, db=db, tier=body.tier, items=[i.model_dump() for i in body.items])


@router.get("/selling-prices")
def selling_prices(tier: str | None = None, db: Session = Depends(get_db)):
    """Map material_id -> unit selling price (consumed by procurement /analyze)."""
    return _run(service.selling_prices, db=db, tier=tier)
