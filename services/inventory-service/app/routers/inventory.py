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


def _stock(item) -> schemas.StockOut:
    return schemas.StockOut(
        material_id=item.material_id, on_hand=float(item.on_hand), reserved=float(item.reserved),
        available=float(item.available), avg_cost=float(item.avg_cost), updated_at=item.updated_at,
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
def list_stock(db: Session = Depends(get_db)):
    return [_stock(i) for i in service.list_stock(db)]


@router.get("/inventory/{material_id}", response_model=schemas.StockOut)
def get_stock(material_id: str, db: Session = Depends(get_db)):
    item = service.get_item(db, material_id)
    if item is None:
        raise HTTPException(404, f"No inventory for material {material_id}")
    return _stock(item)


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
