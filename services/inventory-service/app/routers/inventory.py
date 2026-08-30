"""Inventory REST API."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas, service
from ..auth import current_user, require_role
from ..db import get_db

# Any authenticated user (or service) may read; only hub staff / internal services may mutate stock.
HUB_WRITE = require_role("service", "hub_supervisor", "hub_manager")
router = APIRouter(tags=["inventory"], dependencies=[Depends(current_user)])

# The field team (spoke / site engineer / architect / finance) must never see the hub's cost or avg
# cost price - only quantities (and, elsewhere, the hub's selling price). Cost stays with hub staff
# and internal services (pricing computes selling price from it server-side).
COST_HIDDEN_ROLES = {"spokesperson", "site_engineer", "architect", "finance"}


def _hide_cost(user: dict) -> bool:
    return (user or {}).get("role") in COST_HIDDEN_ROLES


def _stock(item, hide_cost: bool = False) -> schemas.StockOut:
    return schemas.StockOut(
        material_id=item.material_id, on_hand=float(item.on_hand), reserved=float(item.reserved),
        available=float(item.available), avg_cost=0.0 if hide_cost else float(item.avg_cost),
        updated_at=item.updated_at,
    )


def _pstock(ps, hide_cost: bool = False) -> schemas.ProductStockOut:
    return schemas.ProductStockOut(
        product_id=ps.product_id, material_id=ps.material_id, on_hand=float(ps.on_hand),
        reserved=float(ps.reserved), available=float(ps.available),
        avg_cost=0.0 if hide_cost else float(ps.avg_cost), updated_at=ps.updated_at,
    )


@router.get("/materials", response_model=list[schemas.MaterialOut])
def list_materials(db: Session = Depends(get_db)):
    """Canonical materials catalog (owned by inventory-service; see Q11)."""
    return service.list_materials(db)


@router.get("/products/search", response_model=list[schemas.ProductOut])
def search_products(q: str = "", limit: int = 25, db: Session = Depends(get_db)):
    """Full product-name search across brands (e.g. q='ultratech 53')."""
    return service.search_products(db, q, limit)


@router.get("/products", response_model=list[schemas.ProductOut])
def list_products(material_id: str | None = None, db: Session = Depends(get_db)):
    """Branded products, optionally filtered by material."""
    return service.list_products(db, material_id)


@router.post("/products", response_model=schemas.ProductOut, status_code=201, dependencies=[Depends(HUB_WRITE)])
def create_product(body: schemas.ProductIn, db: Session = Depends(get_db)):
    """Add a new branded product (SKU) to the catalog."""
    try:
        return service.create_product(db, body.material_id, body.name, body.brand, body.grade, body.unit)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/products/{product_id}", response_model=schemas.ProductOut)
def get_product(product_id: str, db: Session = Depends(get_db)):
    p = service.get_product(db, product_id)
    if p is None:
        raise HTTPException(404, f"Unknown product: {product_id}")
    return p


@router.get("/inventory", response_model=list[schemas.StockOut])
def list_stock(user: dict = Depends(current_user), db: Session = Depends(get_db)):
    hide = _hide_cost(user)
    return [_stock(i, hide) for i in service.list_stock(db)]


@router.get("/inventory/{material_id}", response_model=schemas.StockOut)
def get_stock(material_id: str, user: dict = Depends(current_user), db: Session = Depends(get_db)):
    item = service.get_item(db, material_id)
    if item is None:
        raise HTTPException(404, f"No inventory for material {material_id}")
    return _stock(item, _hide_cost(user))


# ---- Product-level (brand SKU) stock ----

@router.get("/product-stock", response_model=list[schemas.ProductStockOut])
def list_product_stock(material_id: str | None = None, user: dict = Depends(current_user), db: Session = Depends(get_db)):
    """Per-brand stock positions, optionally filtered by material."""
    hide = _hide_cost(user)
    return [_pstock(ps, hide) for ps in service.list_product_stock(db, material_id)]


@router.get("/product-stock/low", response_model=list[schemas.LowStockOut])
def low_stock(db: Session = Depends(get_db)):
    """Products under the hub's 3x-reserved buffer (early low/no-stock signal)."""
    return service.low_stock_products(db)


@router.get("/product-stock/{product_id}", response_model=schemas.ProductStockOut)
def get_product_stock(product_id: str, user: dict = Depends(current_user), db: Session = Depends(get_db)):
    ps = service.get_product_stock(db, product_id)
    if ps is None:
        raise HTTPException(404, f"No stock for product {product_id}")
    return _pstock(ps, _hide_cost(user))


@router.get("/inventory/{material_id}/ledger", response_model=list[schemas.LedgerOut])
def item_ledger(material_id: str, limit: int = 100, db: Session = Depends(get_db)):
    return service.ledger(db, material_id, limit)


@router.get("/ledger", response_model=list[schemas.LedgerOut])
def all_ledger(limit: int = 100, db: Session = Depends(get_db)):
    return service.ledger(db, None, limit)


def _run(fn, **kwargs):
    try:
        return fn(**kwargs)
    except service.InventoryError as e:
        raise HTTPException(409, str(e))


@router.post("/inventory/inbound", response_model=schemas.LedgerOut, dependencies=[Depends(HUB_WRITE)])
def inbound(body: schemas.InboundIn, db: Session = Depends(get_db)):
    return _run(service.receive, db=db, material_id=body.material_id, qty=body.qty,
                unit_cost=body.unit_cost, ref_type=body.ref_type, ref_id=body.ref_id, note=body.note)


@router.post("/inventory/outbound", response_model=schemas.LedgerOut, dependencies=[Depends(HUB_WRITE)])
def outbound(body: schemas.OutboundIn, db: Session = Depends(get_db)):
    return _run(service.dispatch, db=db, material_id=body.material_id, qty=body.qty,
                ref_type=body.ref_type, ref_id=body.ref_id, note=body.note,
                from_reservation=body.from_reservation)


@router.post("/inventory/product-inbound", response_model=schemas.ProductStockOut, dependencies=[Depends(HUB_WRITE)])
def product_inbound(body: schemas.InboundIn, db: Session = Depends(get_db)):
    """Brand-level receipt (procurement receives a specific product). Rolls up to the material."""
    if not body.product_id:
        raise HTTPException(422, "product_id is required")
    return _pstock(_run(service.receive_product, db=db, product_id=body.product_id, qty=body.qty,
                        unit_cost=body.unit_cost, ref_type=body.ref_type, ref_id=body.ref_id, note=body.note))


@router.post("/inventory/product-outbound", response_model=schemas.ProductStockOut, dependencies=[Depends(HUB_WRITE)])
def product_outbound(body: schemas.OutboundIn, db: Session = Depends(get_db)):
    """Brand-level dispatch to a site. Rolls up to the material."""
    if not body.product_id:
        raise HTTPException(422, "product_id is required")
    return _pstock(_run(service.dispatch_product, db=db, product_id=body.product_id, qty=body.qty,
                        ref_type=body.ref_type, ref_id=body.ref_id, note=body.note,
                        from_reservation=body.from_reservation))


@router.post("/inventory/product-reserve", response_model=schemas.ProductStockOut, dependencies=[Depends(HUB_WRITE)])
def product_reserve(body: schemas.ReserveIn, db: Session = Depends(get_db)):
    if not body.product_id:
        raise HTTPException(422, "product_id is required")
    return _pstock(_run(service.reserve_product, db=db, product_id=body.product_id, qty=body.qty,
                        allow_over=body.allow_over))


@router.post("/inventory/product-release", response_model=schemas.ProductStockOut, dependencies=[Depends(HUB_WRITE)])
def product_release(body: schemas.ReserveIn, db: Session = Depends(get_db)):
    if not body.product_id:
        raise HTTPException(422, "product_id is required")
    return _pstock(_run(service.release_product, db=db, product_id=body.product_id, qty=body.qty))


@router.post("/inventory/adjust", response_model=schemas.LedgerOut, dependencies=[Depends(HUB_WRITE)])
def adjust(body: schemas.AdjustIn, db: Session = Depends(get_db)):
    return _run(service.adjust, db=db, material_id=body.material_id, qty_delta=body.qty_delta,
                note=body.note)


@router.post("/inventory/reserve", response_model=schemas.StockOut, dependencies=[Depends(HUB_WRITE)])
def reserve(body: schemas.ReserveIn, db: Session = Depends(get_db)):
    item = _run(service.reserve, db=db, material_id=body.material_id, qty=body.qty)
    return _stock(item)


@router.post("/inventory/release", response_model=schemas.StockOut, dependencies=[Depends(HUB_WRITE)])
def release(body: schemas.ReserveIn, db: Session = Depends(get_db)):
    item = _run(service.release, db=db, material_id=body.material_id, qty=body.qty)
    return _stock(item)
