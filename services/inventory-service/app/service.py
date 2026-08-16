"""Inventory domain logic.

All mutations are transactional and lock the item row (SELECT ... FOR UPDATE) to prevent
oversell/lost-update under concurrency. `on_hand` and `avg_cost` are maintained alongside an
append-only ledger; every movement writes exactly one LedgerEntry with the resulting balance.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
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
          unit_cost: Decimal, ref_type: str, ref_id: str, note: str) -> models.LedgerEntry:
    entry = models.LedgerEntry(
        material_id=item.material_id, direction=direction, qty=qty, unit_cost=unit_cost,
        balance_after=item.on_hand, ref_type=ref_type, ref_id=ref_id, note=note,
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


def list_stock(db: Session) -> list[models.InventoryItem]:
    return list(db.execute(select(models.InventoryItem)).scalars())


def get_item(db: Session, material_id: str) -> models.InventoryItem | None:
    return db.get(models.InventoryItem, material_id)


def ledger(db: Session, material_id: str | None = None, limit: int = 100) -> list[models.LedgerEntry]:
    stmt = select(models.LedgerEntry).order_by(models.LedgerEntry.id.desc()).limit(limit)
    if material_id:
        stmt = stmt.where(models.LedgerEntry.material_id == material_id)
    return list(db.execute(stmt).scalars())
