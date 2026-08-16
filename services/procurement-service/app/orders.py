"""Procurement order lifecycle: create, list, and receive-into-inventory."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models, service
from .inventory_client import InventoryUnavailable, post_inbound


def _dec(x) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


def create_order(db: Session, lines: list[dict], *, status: str = models.PO_APPROVED,
                 note: str = "") -> models.ProcurementOrder:
    """lines: [{material_id, vendor_id, qty, unit_cost}]. Validates vendors, computes total."""
    if not lines:
        raise service.ProcurementError("A procurement order needs at least one line")
    order = models.ProcurementOrder(status=status, note=note, total_cost=Decimal("0"))
    db.add(order)
    db.flush()  # assign id
    total = Decimal("0")
    for ln in lines:
        vendor = db.get(models.Vendor, ln["vendor_id"])
        if vendor is None:
            raise service.ProcurementError(f"Unknown vendor: {ln['vendor_id']}")
        qty, unit_cost = _dec(ln["qty"]), _dec(ln["unit_cost"])
        if qty <= 0 or unit_cost < 0:
            raise service.ProcurementError("Line qty must be > 0 and unit_cost >= 0")
        total += (qty * unit_cost)
        db.add(models.ProcurementLine(
            order_id=order.id, material_id=ln["material_id"], vendor_id=vendor.id,
            vendor_name=vendor.name, qty=qty, unit_cost=unit_cost,
        ))
    order.total_cost = total.quantize(Decimal("0.01"))
    db.commit()
    db.refresh(order)
    return order


def list_orders(db: Session, status: str | None = None) -> list[models.ProcurementOrder]:
    stmt = select(models.ProcurementOrder).order_by(models.ProcurementOrder.id.desc())
    if status:
        stmt = stmt.where(models.ProcurementOrder.status == status)
    return list(db.execute(stmt).scalars())


def get_order(db: Session, order_id: int) -> models.ProcurementOrder | None:
    return db.get(models.ProcurementOrder, order_id)


def receive_order(db: Session, order_id: int) -> models.ProcurementOrder:
    """Post each not-yet-received line to inventory-service as an inbound, then mark received.

    Per-line `received` flags make this idempotent/retry-safe: a re-run skips lines already posted,
    so a partial failure can be retried without double-counting stock.
    """
    order = db.get(models.ProcurementOrder, order_id)
    if order is None:
        raise service.ProcurementError(f"Unknown order: PO-{order_id}")
    if order.status == models.PO_CANCELLED:
        raise service.ProcurementError("Cannot receive a cancelled order")

    for line in order.lines:
        if line.received:
            continue
        try:
            post_inbound(line.material_id, float(line.qty), float(line.unit_cost), order.code)
        except InventoryUnavailable as e:
            db.commit()  # persist any lines already marked received this run
            raise service.ProcurementError(
                f"Received {sum(1 for l in order.lines if l.received)}/{len(order.lines)} lines; "
                f"stopped at {line.material_id}: {e}"
            )
        line.received = True

    if all(l.received for l in order.lines):
        order.status = models.PO_RECEIVED
        from sqlalchemy import func
        order.received_at = db.execute(select(func.now())).scalar()
    db.commit()
    db.refresh(order)
    return order
