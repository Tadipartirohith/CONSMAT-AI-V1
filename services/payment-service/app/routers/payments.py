"""Payment REST API."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas, service
from ..auth import current_user, require_role
from ..config import payment_config
from ..db import get_db

# A payer (consumer) or hub/field staff may initiate a payment; reads for any authenticated user.
PAYER = require_role("consumer", "hub_manager", "hub_supervisor", "spokesperson")
router = APIRouter(tags=["payments"], dependencies=[Depends(current_user)])


def _run(fn, **kwargs):
    try:
        return fn(**kwargs)
    except service.PaymentError as e:
        raise HTTPException(409, str(e))


@router.get("/payments/config", response_model=schemas.ConfigOut)
def config():
    """Active gateway (non-secret) for the UI."""
    cfg = payment_config()
    return {"provider": cfg.get("provider", "mock"), "currency": cfg.get("currency", "INR"),
            "enabled": cfg.get("enabled", True)}


@router.post("/payments", response_model=schemas.PaymentOut, status_code=201, dependencies=[Depends(PAYER)])
def create_payment(body: schemas.PaymentIn, db: Session = Depends(get_db)):
    return _run(service.create_payment, db=db, ref=body.ref, consumer_id=body.consumer_id,
                amount=body.amount, currency=body.currency, note=body.note)


@router.post("/payments/{payment_id}/confirm", response_model=schemas.PaymentOut, dependencies=[Depends(PAYER)])
def confirm_payment(payment_id: int, db: Session = Depends(get_db)):
    return _run(service.confirm_payment, db=db, payment_id=payment_id)


@router.get("/payments", response_model=list[schemas.PaymentOut])
def list_payments(consumer_id: str | None = None, ref: str | None = None, db: Session = Depends(get_db)):
    return service.list_payments(db, consumer_id=consumer_id, ref=ref)


@router.get("/payments/{payment_id}", response_model=schemas.PaymentOut)
def get_payment(payment_id: int, db: Session = Depends(get_db)):
    pay = service.get_payment(db, payment_id)
    if pay is None:
        raise HTTPException(404, f"Unknown payment: PAY-{payment_id}")
    return pay
