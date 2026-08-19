"""Vendor registry + price-list domain logic."""
from __future__ import annotations

import re
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import catalog_client, models, price_scout


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


# ---- Vendor add/remove requests (ops requests -> supervisor/manager approves) ----

VENDOR_APPROVERS = ("hub_supervisor", "hub_manager", "admin")


def create_vendor_request(db: Session, action: str, *, requested_by_role: str, requested_by: str,
                          name: str = "", city: str = "", phone: str = "", gstin: str = "",
                          is_hub_self: bool = False, vendor_id: str = "",
                          reason: str = "") -> models.VendorRequest:
    if action not in (models.VR_ADD, models.VR_REMOVE):
        raise ProcurementError("action must be 'add' or 'remove'")
    if action == models.VR_ADD and not name.strip():
        raise ProcurementError("Vendor name is required to request an add")
    if action == models.VR_REMOVE:
        _require(db, vendor_id)  # target must exist
    req = models.VendorRequest(
        action=action, vendor_id=vendor_id, name=name.strip(), city=city, phone=phone, gstin=gstin,
        is_hub_self=is_hub_self, reason=reason, requested_by_role=requested_by_role,
        requested_by=requested_by)
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


def list_vendor_requests(db: Session, status: str | None = None) -> list[models.VendorRequest]:
    stmt = select(models.VendorRequest).order_by(models.VendorRequest.id.desc())
    if status:
        stmt = stmt.where(models.VendorRequest.status == status)
    return list(db.execute(stmt).scalars())


def decide_vendor_request(db: Session, req_id: int, approve: bool, *, decided_by_role: str,
                          decided_by: str) -> models.VendorRequest:
    """Supervisor/manager approves or rejects. Approving an add creates the vendor; a remove deactivates it."""
    if decided_by_role not in VENDOR_APPROVERS:
        raise ProcurementError("Only a hub supervisor or manager can decide vendor requests")
    req = db.get(models.VendorRequest, req_id)
    if req is None:
        raise ProcurementError(f"Unknown vendor request: {req_id}")
    if req.status != models.VR_PENDING:
        raise ProcurementError("This request has already been decided")
    if approve:
        if req.action == models.VR_ADD:
            v = create_vendor(db, req.name, city=req.city, phone=req.phone, gstin=req.gstin,
                              is_hub_self=req.is_hub_self)
            req.vendor_id = v.id
        else:  # remove
            deactivate_vendor(db, req.vendor_id)
        req.status = models.VR_APPROVED
    else:
        req.status = models.VR_REJECTED
    from sqlalchemy import func as _func
    req.decided_by_role = decided_by_role
    req.decided_by = decided_by
    req.decided_at = db.execute(select(_func.now())).scalar()
    db.commit()
    db.refresh(req)
    return req


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


def run_scout(db: Session, material_id: str, material_name: str = "") -> dict:
    """Price-scout external market intelligence for a material and store the offers (advisory)."""
    brands = sorted({p.brand for p in db.execute(
        select(models.VendorPrice).where(models.VendorPrice.material_id == material_id)
    ).scalars() if p.brand})
    offers, provider = price_scout.scout(material_id, material_name, brands)
    # refresh indicative offers for this material (keep firm/imported ones)
    db.query(models.ExternalOffer).filter(
        models.ExternalOffer.material_id == material_id,
        models.ExternalOffer.confidence == "indicative",
    ).delete()
    for o in offers:
        db.add(models.ExternalOffer(
            material_id=material_id, product_name=o["product_name"], source=provider,
            seller=o["seller"], price=_dec(o["price"]), url=o["url"],
            confidence="indicative", note=o["note"],
        ))
    db.commit()
    return {"provider": provider, "material_id": material_id, "count": len(offers)}


def list_external_offers(db: Session, material_id: str | None = None) -> list[models.ExternalOffer]:
    stmt = select(models.ExternalOffer).order_by(models.ExternalOffer.price.asc())
    if material_id:
        stmt = stmt.where(models.ExternalOffer.material_id == material_id)
    return list(db.execute(stmt).scalars())


def import_offers(db: Session, offers: list[dict]) -> int:
    """Ingest a supplier price list (firm external offers), e.g. from a CSV upload."""
    n = 0
    for o in offers:
        if not o.get("material_id") or o.get("price") is None:
            continue
        db.add(models.ExternalOffer(
            material_id=o["material_id"], product_name=o.get("product_name", ""), source="csv",
            seller=o.get("seller", ""), price=_dec(o["price"]), url=o.get("url", ""),
            confidence="firm", note=o.get("note", "price list"),
        ))
        n += 1
    db.commit()
    return n


# ---- Open-market watch: price drops + alerts ----

_ALERT_OPS = {"lt": lambda a, b: a < b, "lte": lambda a, b: a <= b, "gt": lambda a, b: a > b,
              "gte": lambda a, b: a >= b, "eq": lambda a, b: a == b}


def price_drops(db: Session) -> list[dict]:
    """Products whose current hub avg cost is beaten by an open-market offer in the same category.

    e.g. a brand's stocked avg cost is 350 while an external offer sits at 300 -> surfaced as a saving.
    """
    try:
        stocks = catalog_client.list_product_stock()
        products = {p["id"]: p for p in catalog_client.list_products()}
    except catalog_client.CatalogError:
        stocks, products = [], {}
    by_mat: dict[str, list] = {}
    for o in list_external_offers(db):
        by_mat.setdefault(o.material_id, []).append(o)
    out, seen = [], set()
    for s in stocks:
        avg = float(s.get("avg_cost") or 0)
        if avg <= 0:
            continue
        pid = s["product_id"]
        prod = products.get(pid, {})
        for o in by_mat.get(s.get("material_id", ""), []):
            price = float(o.price)
            if price >= avg or (pid, o.id) in seen:
                continue
            seen.add((pid, o.id))
            saving = avg - price
            out.append({
                "product_id": pid, "product_name": prod.get("name", pid), "brand": prod.get("brand", ""),
                "material_id": s.get("material_id", ""), "avg_cost": round(avg, 2),
                "seller": o.seller, "offer_price": price, "url": o.url, "source": o.source,
                "confidence": o.confidence, "saving": round(saving, 2),
                "saving_pct": round(saving / avg * 100, 1),
            })
    out.sort(key=lambda x: x["saving_pct"], reverse=True)
    return out


def create_alert(db: Session, *, material_id: str = "", query: str = "", op: str = "lt",
                 value: float, seller: str = "", location: str = "") -> models.MarketAlert:
    if op not in _ALERT_OPS:
        raise ProcurementError(f"op must be one of {list(_ALERT_OPS)}")
    a = models.MarketAlert(material_id=material_id, query=query, op=op, value=_dec(value),
                           seller=seller, location=location)
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def delete_alert(db: Session, alert_id: int) -> None:
    a = db.get(models.MarketAlert, alert_id)
    if a is not None:
        db.delete(a)
        db.commit()


def evaluate_alerts(db: Session) -> list[dict]:
    """For each active alert, return the external offers that currently match it."""
    alerts = list(db.execute(select(models.MarketAlert).where(models.MarketAlert.active.is_(True))
                             .order_by(models.MarketAlert.id.desc())).scalars())
    offers = list_external_offers(db)
    result = []
    for al in alerts:
        matches = []
        for o in offers:
            if al.material_id and o.material_id != al.material_id:
                continue
            if al.query and al.query.lower() not in (o.product_name or "").lower():
                continue
            if al.seller and al.seller.lower() not in (o.seller or "").lower():
                continue
            if al.location and al.location.lower() not in f"{o.seller} {o.note}".lower():
                continue
            if not _ALERT_OPS[al.op](float(o.price), float(al.value)):
                continue
            matches.append({"material_id": o.material_id, "seller": o.seller, "product_name": o.product_name,
                            "price": float(o.price), "url": o.url, "source": o.source})
        result.append({
            "alert": {"id": al.id, "material_id": al.material_id, "query": al.query, "op": al.op,
                      "value": float(al.value), "seller": al.seller, "location": al.location},
            "matches": matches,
        })
    return result


def scan_markets(db: Session, materials: list[str]) -> dict:
    """Refresh external offers by scouting each material. Returns per-material counts."""
    total, provider = 0, ""
    for mid in materials:
        r = run_scout(db, mid, mid)
        total += r["count"]
        provider = r["provider"]
    return {"scanned": materials, "offers": total, "provider": provider}


def market_prices(db: Session, material_id: str) -> list[dict]:
    """Cheapest-first view of every active vendor's branded-product price for a material.

    Several companies compete per material (e.g. UltraTech vs ACC cement), each row is a product+vendor
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


def product_offers(db: Session, product_id: str) -> list[dict]:
    """Cheapest-first vendor offers for one specific product (brand SKU)."""
    rows = db.execute(
        select(models.VendorPrice, models.Vendor)
        .join(models.Vendor, models.Vendor.id == models.VendorPrice.vendor_id)
        .where(models.VendorPrice.product_id == product_id, models.Vendor.active.is_(True))
        .order_by(models.VendorPrice.price.asc())
    ).all()
    return [
        {"vendor_id": v.id, "vendor_name": v.name, "is_hub_self": v.is_hub_self,
         "material_id": p.material_id, "product_id": p.product_id, "brand": p.brand,
         "product_name": p.product_name, "price": float(p.price), "min_qty": float(p.min_qty),
         "city": v.city}
        for p, v in rows
    ]
