"""Payment domain logic."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import models, payments
from .config import payment_config


class PaymentError(Exception):
    """Invalid payment operation."""


def _dec(x) -> Decimal:
    return x if isinstance(x, Decimal) else Decimal(str(x))


def create_payment(db: Session, *, ref: str, consumer_id: str, amount, currency: str = "",
                   note: str = "", escrow: bool = True) -> models.Payment:
    cfg = payment_config()
    if not cfg.get("enabled", True):
        raise PaymentError("Payments are disabled")
    amount = _dec(amount)
    if amount <= 0:
        raise PaymentError("Amount must be positive")
    result = payments.charge(float(amount))
    pay = models.Payment(
        ref=ref, consumer_id=consumer_id, amount=amount,
        currency=currency or cfg.get("currency", "INR"),
        provider=result["provider"], provider_ref=result["provider_ref"],
        status=result["status"], note=note or result["note"],
    )
    if pay.status == models.PAID:
        pay.paid_at = db.execute(select(func.now())).scalar()
        # Escrow: funds are captured but HELD, released to the supplier only as deliveries are confirmed.
        if escrow:
            pay.status = models.HELD
            pay.note = note or "captured into escrow; released on delivery confirmation"
    db.add(pay)
    db.commit()
    db.refresh(pay)
    return pay


def release_for_ref(db: Session, ref: str, fraction: float) -> dict:
    """Release escrow for a project ref up to `fraction` of each held payment (0..1).

    Called when a delivery is confirmed at the site: as more phases are delivered, fraction rises to 1
    and the payment flips from `held` to `released`. Idempotent and monotonic (never claws back)."""
    frac = max(0.0, min(1.0, float(fraction)))
    rows = list(db.execute(
        select(models.Payment).where(models.Payment.ref == ref,
                                     models.Payment.status == models.HELD)).scalars())
    released = 0
    for pay in rows:
        target = (pay.amount * _dec(frac)).quantize(Decimal("0.01"))
        if target <= pay.released_amount:
            continue
        pay.released_amount = target
        if pay.released_amount >= pay.amount:
            pay.released_amount = pay.amount
            pay.status = models.RELEASED
            pay.released_at = db.execute(select(func.now())).scalar()
        released += 1
    if released:
        db.commit()
    return {"ref": ref, "fraction": frac, "payments_updated": released}


def confirm_payment(db: Session, payment_id: int) -> models.Payment:
    pay = db.get(models.Payment, payment_id)
    if pay is None:
        raise PaymentError(f"Unknown payment: PAY-{payment_id}")
    if pay.status == models.PAID:
        return pay
    new_status = payments.confirm(pay.provider)
    pay.status = new_status
    if new_status == models.PAID:
        pay.paid_at = db.execute(select(func.now())).scalar()
    db.commit()
    db.refresh(pay)
    return pay


def list_payments(db: Session, *, consumer_id: str | None = None, ref: str | None = None) -> list[models.Payment]:
    stmt = select(models.Payment).order_by(models.Payment.id.desc())
    if consumer_id:
        stmt = stmt.where(models.Payment.consumer_id == consumer_id)
    if ref:
        stmt = stmt.where(models.Payment.ref == ref)
    return list(db.execute(stmt).scalars())


def get_payment(db: Session, payment_id: int) -> models.Payment | None:
    return db.get(models.Payment, payment_id)
