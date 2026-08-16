"""Vendor registry + price-list domain logic."""
from __future__ import annotations

import re
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import catalog_client, models


class ProcurementError(Exception):
    """Raised on invalid vendor/price operations."""


def _dec(x) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


def _slug(name: str) -> str:
    first = (name.strip().lower().split() or ["vendor"])[0]
    return re.sub(r"[^a-z0-9]+", "", first) or "vendor"


def create_vendor(db: Session, name: str, *, city: str = "", phone: str = "", gstin: str = "",
                  is_hub_self: bool = False) -> models.Vendor:
    if not name.strip():
        raise ProcurementError("Vendor name is required")
    base = "v_" + _slug(name)
    vid, n = base, 1
    while db.get(models.Vendor, vid) is not None:
        n += 1
        vid = f"{base}{n}"
    vendor = models.Vendor(id=vid, name=name.strip(), city=city, phone=phone, gstin=gstin,
                           is_hub_self=is_hub_self)
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return vendor


def list_vendors(db: Session, active_only: bool = False) -> list[models.Vendor]:
    stmt = select(models.Vendor).order_by(models.Vendor.name)
    if active_only:
        stmt = stmt.where(models.Vendor.active.is_(True))
    return list(db.execute(stmt).scalars())


def get_vendor(db: Session, vendor_id: str) -> models.Vendor | None:
    return db.get(models.Vendor, vendor_id)


def _require(db: Session, vendor_id: str) -> models.Vendor:
    v = db.get(models.Vendor, vendor_id)
    if v is None:
        raise ProcurementError(f"Unknown vendor: {vendor_id}")
    return v


def update_vendor(db: Session, vendor_id: str, **fields) -> models.Vendor:
    v = _require(db, vendor_id)
    for k in ("name", "city", "phone", "gstin", "active"):
        if k in fields and fields[k] is not None:
            setattr(v, k, fields[k])
    db.commit()
    db.refresh(v)
    return v


def deactivate_vendor(db: Session, vendor_id: str) -> models.Vendor:
    v = _require(db, vendor_id)
    v.active = False
    db.commit()
    db.refresh(v)
    return v


def set_price(db: Session, vendor_id: str, product_id: str, price, min_qty=0) -> models.VendorPrice:
    """Upsert a vendor's price for a branded product. Denormalizes material/brand/name from the catalog."""
    _require(db, vendor_id)
    price = _dec(price)
    if price < 0:
        raise ProcurementError("Price cannot be negative")
    product = catalog_client.get_product(product_id)
    if product is None:
        raise ProcurementError(f"Unknown product: {product_id}")
    row = db.execute(
        select(models.VendorPrice).where(
            models.VendorPrice.vendor_id == vendor_id,
            models.VendorPrice.product_id == product_id,
        )
    ).scalar_one_or_none()
    if row is None:
        row = models.VendorPrice(vendor_id=vendor_id, product_id=product_id,
                                 material_id=product["material_id"], brand=product.get("brand", ""),
                                 product_name=product["name"], price=price, min_qty=_dec(min_qty))
        db.add(row)
    else:
        row.price = price
        row.min_qty = _dec(min_qty)
    db.commit()
    db.refresh(row)
    return row


def delete_price(db: Session, vendor_id: str, product_id: str) -> None:
    row = db.execute(
        select(models.VendorPrice).where(
            models.VendorPrice.vendor_id == vendor_id,
            models.VendorPrice.product_id == product_id,
        )
    ).scalar_one_or_none()
    if row is None:
        raise ProcurementError(f"No price for {product_id} from {vendor_id}")
    db.delete(row)
    db.commit()


def market_prices(db: Session, material_id: str) -> list[dict]:
    """Cheapest-first view of every active vendor's branded-product price for a material.

    Several companies compete per material (e.g. UltraTech vs ACC cement) — each row is a product+vendor
    offer. This is the signal the procurement engine + Hub LLM rank.
    """
    rows = db.execute(
        select(models.VendorPrice, models.Vendor)
        .join(models.Vendor, models.Vendor.id == models.VendorPrice.vendor_id)
        .where(models.VendorPrice.material_id == material_id, models.Vendor.active.is_(True))
        .order_by(models.VendorPrice.price.asc())
    ).all()
    return [
        {"vendor_id": v.id, "vendor_name": v.name, "is_hub_self": v.is_hub_self,
         "material_id": material_id, "product_id": p.product_id, "brand": p.brand,
         "product_name": p.product_name, "price": float(p.price), "min_qty": float(p.min_qty),
         "city": v.city}
        for p, v in rows
    ]
