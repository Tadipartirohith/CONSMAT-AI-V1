"""Vendor registry + price-list REST API."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas, service
from ..db import get_db

router = APIRouter(tags=["procurement"])


def _run(fn, **kwargs):
    try:
        return fn(**kwargs)
    except service.ProcurementError as e:
        raise HTTPException(409, str(e))


@router.post("/vendors", response_model=schemas.VendorDetailOut, status_code=201)
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


@router.patch("/vendors/{vendor_id}", response_model=schemas.VendorDetailOut)
def update_vendor(vendor_id: str, body: schemas.VendorUpdate, db: Session = Depends(get_db)):
    return _run(service.update_vendor, db=db, vendor_id=vendor_id, **body.model_dump(exclude_unset=True))


@router.delete("/vendors/{vendor_id}", response_model=schemas.VendorDetailOut)
def deactivate_vendor(vendor_id: str, db: Session = Depends(get_db)):
    """Soft-deactivate (keeps history); reactivate via PATCH active=true."""
    return _run(service.deactivate_vendor, db=db, vendor_id=vendor_id)


@router.put("/vendors/{vendor_id}/prices", response_model=schemas.PriceOut)
def set_price(vendor_id: str, body: schemas.PriceIn, db: Session = Depends(get_db)):
    return _run(service.set_price, db=db, vendor_id=vendor_id, material_id=body.material_id,
                price=body.price, min_qty=body.min_qty)


@router.delete("/vendors/{vendor_id}/prices/{material_id}", status_code=204)
def delete_price(vendor_id: str, material_id: str, db: Session = Depends(get_db)):
    _run(service.delete_price, db=db, vendor_id=vendor_id, material_id=material_id)


@router.get("/prices/{material_id}", response_model=list[schemas.MarketPriceOut])
def market_prices(material_id: str, db: Session = Depends(get_db)):
    """Cheapest-first market view for a material across all active vendors."""
    return service.market_prices(db, material_id)
