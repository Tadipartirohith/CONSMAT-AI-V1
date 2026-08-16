"""Inventory domain logic.

All mutations are transactional and lock the item row (SELECT ... FOR UPDATE) to prevent
oversell/lost-update under concurrency. `on_hand` and `avg_cost` are maintained alongside an
append-only ledger; every movement writes exactly one LedgerEntry with the resulting balance.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import models


class InventoryError(Exception):
    """Raised on invalid inventory operations (e.g. oversell, unknown material)."""


def _dec(x) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


def _get_item_locked(db: Session, material_id: str) -> models.InventoryItem:
    """Fetch the inventory row with a write lock, creating it if the material exists."""
    material = db.get(models.Material, material_id)
    if material is None:
        raise InventoryError(f"Unknown material: {material_id}")
    item = db.execute(
        select(models.InventoryItem)
        .where(models.InventoryItem.material_id == material_id)
        .with_for_update()
    ).scalar_one_or_none()
    if item is None:
        item = models.InventoryItem(material_id=material_id)
        db.add(item)
        db.flush()
    return item


def _post(db: Session, item: models.InventoryItem, direction: str, qty: Decimal,
          unit_cost: Decimal, ref_type: str, ref_id: str, note: str,
          product_id: str = "") -> models.LedgerEntry:
    entry = models.LedgerEntry(
        material_id=item.material_id, product_id=product_id, direction=direction, qty=qty,
        unit_cost=unit_cost, balance_after=item.on_hand, ref_type=ref_type, ref_id=ref_id, note=note,
    )
    db.add(entry)
    return entry


def receive(db: Session, material_id: str, qty, unit_cost, *, ref_type=models.REF_PROCUREMENT,
            ref_id: str = "", note: str = "") -> models.LedgerEntry:
    """Inbound: add stock and update weighted-average cost."""
    qty, unit_cost = _dec(qty), _dec(unit_cost)
    if qty <= 0:
        raise InventoryError("Inbound quantity must be positive")
    item = _get_item_locked(db, material_id)
    new_on_hand = item.on_hand + qty
    # weighted-average cost
    if new_on_hand > 0:
        item.avg_cost = (item.on_hand * item.avg_cost + qty * unit_cost) / new_on_hand
    item.on_hand = new_on_hand
    entry = _post(db, item, models.INBOUND, qty, unit_cost, ref_type, ref_id, note)
    db.commit()
    db.refresh(entry)
    return entry


def dispatch(db: Session, material_id: str, qty, *, ref_type=models.REF_DISPATCH,
             ref_id: str = "", note: str = "", from_reservation: bool = False) -> models.LedgerEntry:
    """Outbound: ship stock to a site at current average cost. Guards against oversell."""
    qty = _dec(qty)
    if qty <= 0:
        raise InventoryError("Outbound quantity must be positive")
    item = _get_item_locked(db, material_id)
    if from_reservation:
        if item.reserved < qty:
            raise InventoryError(
                f"Reserved {item.reserved} < requested {qty} for {material_id}")
        item.reserved -= qty
    available = item.on_hand if from_reservation else item.available
    if available < qty:
        raise InventoryError(
            f"Insufficient stock for {material_id}: available {available}, requested {qty}")
    item.on_hand -= qty
    entry = _post(db, item, models.OUTBOUND, -qty, item.avg_cost, ref_type, ref_id, note)
    db.commit()
    db.refresh(entry)
    return entry


def adjust(db: Session, material_id: str, qty_delta, *, note: str = "") -> models.LedgerEntry:
    """Signed correction (+/-) e.g. stock count or wastage."""
    qty_delta = _dec(qty_delta)
    if qty_delta == 0:
        raise InventoryError("Adjustment cannot be zero")
    item = _get_item_locked(db, material_id)
    if item.on_hand + qty_delta < 0:
        raise InventoryError("Adjustment would drive on_hand negative")
    item.on_hand += qty_delta
    entry = _post(db, item, models.ADJUSTMENT, qty_delta, item.avg_cost,
                  models.REF_ADJUSTMENT, "", note)
    db.commit()
    db.refresh(entry)
    return entry


def reserve(db: Session, material_id: str, qty) -> models.InventoryItem:
    """Reserve available stock for an upcoming dispatch (no ledger movement yet)."""
    qty = _dec(qty)
    if qty <= 0:
        raise InventoryError("Reserve quantity must be positive")
    item = _get_item_locked(db, material_id)
    if item.available < qty:
        raise InventoryError(
            f"Cannot reserve {qty} of {material_id}: available {item.available}")
    item.reserved += qty
    db.commit()
    db.refresh(item)
    return item


def release(db: Session, material_id: str, qty) -> models.InventoryItem:
    """Release a previously held reservation."""
    qty = _dec(qty)
    if qty <= 0:
        raise InventoryError("Release quantity must be positive")
    item = _get_item_locked(db, material_id)
    item.reserved = max(Decimal("0"), item.reserved - qty)
    db.commit()
    db.refresh(item)
    return item


# ---- Product-level stock (brand SKUs). Source of truth per brand; rolls up into the material item. ----

def _get_pstock_locked(db: Session, product_id: str) -> models.ProductStock:
    """Lock the product-stock row, creating it if the product exists."""
    product = db.get(models.Product, product_id)
    if product is None:
        raise InventoryError(f"Unknown product: {product_id}")
    ps = db.execute(
        select(models.ProductStock)
        .where(models.ProductStock.product_id == product_id)
        .with_for_update()
    ).scalar_one_or_none()
    if ps is None:
        ps = models.ProductStock(product_id=product_id, material_id=product.material_id)
        db.add(ps)
        db.flush()
    return ps


def receive_product(db: Session, product_id: str, qty, unit_cost, *, ref_type=models.REF_PROCUREMENT,
                    ref_id: str = "", note: str = "") -> models.ProductStock:
    """Inbound at the brand level. Updates the product's weighted-avg cost and rolls up to the material."""
    qty, unit_cost = _dec(qty), _dec(unit_cost)
    if qty <= 0:
        raise InventoryError("Inbound quantity must be positive")
    ps = _get_pstock_locked(db, product_id)
    item = _get_item_locked(db, ps.material_id)
    for holder in (ps, item):
        new_on_hand = holder.on_hand + qty
        if new_on_hand > 0:
            holder.avg_cost = (holder.on_hand * holder.avg_cost + qty * unit_cost) / new_on_hand
        holder.on_hand = new_on_hand
    _post(db, item, models.INBOUND, qty, unit_cost, ref_type, ref_id, note, product_id=product_id)
    db.commit()
    db.refresh(ps)
    return ps


def dispatch_product(db: Session, product_id: str, qty, *, ref_type=models.REF_DISPATCH,
                     ref_id: str = "", note: str = "", from_reservation: bool = False) -> models.ProductStock:
    """Outbound at the brand level, guarding oversell on the product. Rolls the movement up to material."""
    qty = _dec(qty)
    if qty <= 0:
        raise InventoryError("Outbound quantity must be positive")
    ps = _get_pstock_locked(db, product_id)
    item = _get_item_locked(db, ps.material_id)
    if from_reservation:
        if ps.reserved < qty:
            raise InventoryError(f"Reserved {ps.reserved} < requested {qty} for {product_id}")
        ps.reserved -= qty
        item.reserved = max(Decimal("0"), item.reserved - qty)
    available = ps.on_hand if from_reservation else ps.available
    if available < qty:
        raise InventoryError(
            f"Insufficient stock for {product_id}: available {available}, requested {qty}")
    ps.on_hand -= qty
    item.on_hand -= qty
    _post(db, item, models.OUTBOUND, -qty, ps.avg_cost, ref_type, ref_id, note, product_id=product_id)
    db.commit()
    db.refresh(ps)
    return ps


def reserve_product(db: Session, product_id: str, qty, *, allow_over: bool = False) -> models.ProductStock:
    """Reserve brand stock for committed demand (no ledger movement).

    With allow_over=True the reservation represents *requested* demand and may exceed on-hand (so the
    hub's 3x buffer surfaces low/no-stock early rather than blocking the request); otherwise it guards
    against reserving more than is available.
    """
    qty = _dec(qty)
    if qty <= 0:
        raise InventoryError("Reserve quantity must be positive")
    ps = _get_pstock_locked(db, product_id)
    if not allow_over and ps.available < qty:
        raise InventoryError(f"Cannot reserve {qty} of {product_id}: available {ps.available}")
    item = _get_item_locked(db, ps.material_id)
    ps.reserved += qty
    item.reserved += qty
    db.commit()
    db.refresh(ps)
    return ps


def release_product(db: Session, product_id: str, qty) -> models.ProductStock:
    """Release a previously held brand reservation."""
    qty = _dec(qty)
    if qty <= 0:
        raise InventoryError("Release quantity must be positive")
    ps = _get_pstock_locked(db, product_id)
    item = _get_item_locked(db, ps.material_id)
    ps.reserved = max(Decimal("0"), ps.reserved - qty)
    item.reserved = max(Decimal("0"), item.reserved - qty)
    db.commit()
    db.refresh(ps)
    return ps


def list_product_stock(db: Session, material_id: str | None = None) -> list[models.ProductStock]:
    stmt = select(models.ProductStock)
    if material_id:
        stmt = stmt.where(models.ProductStock.material_id == material_id)
    return list(db.execute(stmt).scalars())


def get_product_stock(db: Session, product_id: str) -> models.ProductStock | None:
    return db.get(models.ProductStock, product_id)


def low_stock_products(db: Session, buffer_multiple: Decimal = Decimal("3")) -> list[dict]:
    """Products whose on_hand falls below `buffer_multiple` x reserved (the hub's committed demand).

    reserved is the committed/requested quantity; the hub wants to hold 3x that as a buffer. A product
    with reserved > 0 and on_hand < 3x reserved is flagged early (before it actually stocks out).
    """
    out = []
    for ps in db.execute(select(models.ProductStock).where(models.ProductStock.reserved > 0)).scalars():
        target = _dec(ps.reserved) * buffer_multiple
        if _dec(ps.on_hand) < target:
            out.append({
                "product_id": ps.product_id, "material_id": ps.material_id,
                "on_hand": float(ps.on_hand), "reserved": float(ps.reserved),
                "buffer_target": float(target), "shortfall": float(target - _dec(ps.on_hand)),
                "status": "no_stock" if _dec(ps.on_hand) < _dec(ps.reserved) else "low_stock",
            })
    return out


def list_materials(db: Session) -> list[models.Material]:
    return list(db.execute(select(models.Material).order_by(models.Material.id)).scalars())


def create_product(db: Session, material_id: str, name: str, brand: str = "",
                   grade: str = "", unit: str = "") -> models.Product:
    import re
    mat = db.get(models.Material, material_id)
    if mat is None:
        raise ValueError(f"Unknown material: {material_id}")
    if not name.strip():
        raise ValueError("Product name is required")
    base = f"{material_id}-" + (re.sub(r"[^a-z0-9]+", "-", (brand or name).lower()).strip("-")[:40] or "product")
    pid, n = base, 1
    while db.get(models.Product, pid) is not None:
        n += 1
        pid = f"{base}-{n}"
    p = models.Product(id=pid, material_id=material_id, brand=brand.strip(), name=name.strip(),
                       grade=grade.strip(), unit=unit.strip() or mat.unit)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def list_products(db: Session, material_id: str | None = None) -> list[models.Product]:
    stmt = select(models.Product).where(models.Product.active.is_(True)).order_by(models.Product.name)
    if material_id:
        stmt = stmt.where(models.Product.material_id == material_id)
    return list(db.execute(stmt).scalars())


def get_product(db: Session, product_id: str) -> models.Product | None:
    return db.get(models.Product, product_id)


def search_products(db: Session, q: str, limit: int = 25) -> list[models.Product]:
    """Full product-name search: every whitespace-separated term must appear (case-insensitive) in the
    product name, brand, or grade. Ordered by name."""
    from sqlalchemy import or_
    stmt = select(models.Product).where(models.Product.active.is_(True))
    for term in (q or "").split():
        like = f"%{term.lower()}%"
        stmt = stmt.where(or_(
            func.lower(models.Product.name).like(like),
            func.lower(models.Product.brand).like(like),
            func.lower(models.Product.grade).like(like),
        ))
    return list(db.execute(stmt.order_by(models.Product.name).limit(limit)).scalars())


def list_stock(db: Session) -> list[models.InventoryItem]:
    return list(db.execute(select(models.InventoryItem)).scalars())


def get_item(db: Session, material_id: str) -> models.InventoryItem | None:
    return db.get(models.InventoryItem, material_id)


def ledger(db: Session, material_id: str | None = None, limit: int = 100) -> list[models.LedgerEntry]:
    stmt = select(models.LedgerEntry).order_by(models.LedgerEntry.id.desc()).limit(limit)
    if material_id:
        stmt = stmt.where(models.LedgerEntry.material_id == material_id)
    return list(db.execute(stmt).scalars())
