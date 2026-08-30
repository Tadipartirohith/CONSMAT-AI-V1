"""Vendor registry + price-list REST API."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas, service
from ..auth import current_user, require_role
from ..db import get_db

# Reads: any authenticated user. Vendor/price changes + approvals: hub supervisor/manager.
HUB_WRITE = require_role("hub_supervisor", "hub_manager")
# Requesting a vendor add/remove: operators too (approval still gated to supervisor/manager).
HUB_REQUEST = require_role("hub_ops", "hub_supervisor", "hub_manager")
router = APIRouter(tags=["procurement"], dependencies=[Depends(current_user)])


def _run(fn, **kwargs):
    try:
        return fn(**kwargs)
    except service.ProcurementError as e:
        raise HTTPException(409, str(e))


@router.post("/vendors", response_model=schemas.VendorDetailOut, status_code=201, dependencies=[Depends(HUB_WRITE)])
def create_vendor(body: schemas.VendorIn, db: Session = Depends(get_db)):
    return _run(service.create_vendor, db=db, name=body.name, city=body.city, phone=body.phone,
                gstin=body.gstin, is_hub_self=body.is_hub_self)


@router.get("/vendors", response_model=list[schemas.VendorOut])
def list_vendors(active: bool = False, db: Session = Depends(get_db)):
    return service.list_vendors(db, active_only=active)


@router.get("/vendors/{vendor_id}", response_model=schemas.VendorDetailOut)
def get_vendor(vendor_id: str, db: Session = Depends(get_db)):
    v = service.get_vendor(db, vendor_id)
    if v is None:
        raise HTTPException(404, f"Unknown vendor: {vendor_id}")
    return v


@router.patch("/vendors/{vendor_id}", response_model=schemas.VendorDetailOut, dependencies=[Depends(HUB_WRITE)])
def update_vendor(vendor_id: str, body: schemas.VendorUpdate, db: Session = Depends(get_db)):
    return _run(service.update_vendor, db=db, vendor_id=vendor_id, **body.model_dump(exclude_unset=True))


@router.delete("/vendors/{vendor_id}", response_model=schemas.VendorDetailOut, dependencies=[Depends(HUB_WRITE)])
def deactivate_vendor(vendor_id: str, db: Session = Depends(get_db)):
    """Soft-deactivate (keeps history); reactivate via PATCH active=true."""
    return _run(service.deactivate_vendor, db=db, vendor_id=vendor_id)


@router.post("/vendors/{vendor_id}/block", response_model=schemas.VendorDetailOut, dependencies=[Depends(HUB_WRITE)])
def block_vendor(vendor_id: str, db: Session = Depends(get_db)):
    """Blacklist a vendor: excluded from all procurement (market view, plans, orders). Reversible."""
    return _run(service.set_vendor_blocked, db=db, vendor_id=vendor_id, blocked=True)


@router.post("/vendors/{vendor_id}/unblock", response_model=schemas.VendorDetailOut, dependencies=[Depends(HUB_WRITE)])
def unblock_vendor(vendor_id: str, db: Session = Depends(get_db)):
    """Lift a vendor's blacklist."""
    return _run(service.set_vendor_blocked, db=db, vendor_id=vendor_id, blocked=False)


@router.post("/vendor-requests", response_model=schemas.VendorRequestOut, status_code=201, dependencies=[Depends(HUB_REQUEST)])
def create_vendor_request(body: schemas.VendorRequestIn, user: dict = Depends(current_user), db: Session = Depends(get_db)):
    """Operator requests a vendor add/remove; a supervisor or manager approves it."""
    return _run(service.create_vendor_request, db=db, action=body.action, name=body.name, city=body.city,
                phone=body.phone, gstin=body.gstin, is_hub_self=body.is_hub_self, vendor_id=body.vendor_id,
                reason=body.reason, requested_by_role=user.get("role", ""), requested_by=user.get("name", ""))


@router.get("/vendor-requests", response_model=list[schemas.VendorRequestOut])
def list_vendor_requests(status: str | None = None, db: Session = Depends(get_db)):
    return service.list_vendor_requests(db, status)


@router.post("/vendor-requests/{req_id}/decide", response_model=schemas.VendorRequestOut)
def decide_vendor_request(req_id: int, body: schemas.DecideVendorIn, user: dict = Depends(current_user), db: Session = Depends(get_db)):
    """Supervisor/manager approves or rejects. Approving executes the add/remove."""
    return _run(service.decide_vendor_request, db=db, req_id=req_id, approve=body.approve,
                decided_by_role=user.get("role", ""), decided_by=user.get("name", ""))


@router.put("/vendors/{vendor_id}/prices", response_model=schemas.PriceOut, dependencies=[Depends(HUB_WRITE)])
def set_price(vendor_id: str, body: schemas.PriceIn, db: Session = Depends(get_db)):
    return _run(service.set_price, db=db, vendor_id=vendor_id, product_id=body.product_id,
                price=body.price, min_qty=body.min_qty)


@router.delete("/vendors/{vendor_id}/prices/{product_id}", status_code=204, dependencies=[Depends(HUB_WRITE)])
def delete_price(vendor_id: str, product_id: str, db: Session = Depends(get_db)):
    _run(service.delete_price, db=db, vendor_id=vendor_id, product_id=product_id)


@router.get("/prices/{material_id}", response_model=list[schemas.MarketPriceOut])
def market_prices(material_id: str, db: Session = Depends(get_db)):
    """Cheapest-first market view of branded products for a material across all active vendors."""
    return service.market_prices(db, material_id)
